"""A lightweight subset of Pydantic used for local validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, get_args, get_origin, get_type_hints


__all__ = ["BaseModel", "Field", "ValidationError", "validator"]


T = TypeVar("T", bound="BaseModel")
_UNSET = object()


class ValidationError(ValueError):
    """Exception raised when model validation fails."""

    def __init__(self, errors: List[Tuple[str, Any]]):
        normalized: List[Tuple[str, str]] = []
        for field, err in errors:
            message = str(err)
            normalized.append((field, message))
        self._errors = normalized
        message = "; ".join(f"{field}: {msg}" for field, msg in normalized)
        super().__init__(message)

    def errors(self) -> List[Tuple[str, str]]:
        return list(self._errors)


@dataclass
class FieldInfo:
    default: Any = _UNSET
    default_factory: Optional[Any] = None


def Field(*, default: Any = _UNSET, default_factory: Optional[Any] = None) -> FieldInfo:
    if default is not _UNSET and default_factory is not None:
        raise TypeError("Field cannot specify both default and default_factory")
    return FieldInfo(default=default, default_factory=default_factory)


@dataclass
class _ValidatorConfig:
    func: Any
    fields: Tuple[str, ...]
    pre: bool
    each_item: bool
    always: bool


def validator(*fields: str, pre: bool = False, each_item: bool = False, always: bool = False):
    if not fields:
        raise TypeError("validator requires at least one field")

    def decorator(func: Any) -> Any:
        config = _ValidatorConfig(
            func=func,
            fields=tuple(fields),
            pre=pre,
            each_item=each_item,
            always=always,
        )
        setattr(func, "__validator_config__", config)
        return func

    return decorator


@dataclass
class _ModelField:
    name: str
    type_hint: Any
    default: Any = _UNSET
    default_factory: Optional[Any] = None


class _ModelMeta(type):
    def __new__(mcls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]):
        validator_configs: List[_ValidatorConfig] = []
        for base in bases:
            validator_configs.extend(getattr(base, "__validator_configs__", []))

        own_validators: List[_ValidatorConfig] = []
        for attr, value in list(namespace.items()):
            config = getattr(value, "__validator_config__", None)
            if config is not None:
                own_validators.append(config)
                namespace.pop(attr)
        validator_configs.extend(own_validators)

        field_infos: Dict[str, FieldInfo] = {}
        for attr, value in list(namespace.items()):
            if isinstance(value, FieldInfo):
                field_infos[attr] = value
                namespace.pop(attr)

        cls = super().__new__(mcls, name, bases, namespace)

        type_hints = get_type_hints(cls, include_extras=True)
        base_hints: Dict[str, Any] = {}
        for base in bases:
            base_hints.update(get_type_hints(base, include_extras=True))

        own_hints = {name: hint for name, hint in type_hints.items() if name not in base_hints}

        base_fields: Dict[str, _ModelField] = {}
        for base in reversed(bases):
            base_fields.update(getattr(base, "__fields__", {}))

        fields: Dict[str, _ModelField] = {
            name: _ModelField(
                name=field.name,
                type_hint=field.type_hint,
                default=field.default,
                default_factory=field.default_factory,
            )
            for name, field in base_fields.items()
        }

        for field_name, field_type in own_hints.items():
            if field_name.startswith("__"):
                continue
            default = getattr(cls, field_name, _UNSET)
            default_factory: Optional[Any] = None
            info = field_infos.get(field_name)
            if isinstance(default, FieldInfo):
                info = default
                default = _UNSET
            if info is not None:
                if info.default is not _UNSET:
                    default = info.default
                default_factory = info.default_factory
            if default_factory is not None and callable(default_factory):
                pass
            elif default_factory is not None:
                raise TypeError("default_factory must be callable")
            fields[field_name] = _ModelField(
                name=field_name,
                type_hint=field_type,
                default=default,
                default_factory=default_factory,
            )
            if hasattr(cls, field_name):
                delattr(cls, field_name)

        cls.__fields__ = fields
        cls.__validator_configs__ = validator_configs
        cls.__validators__ = _organize_validators(validator_configs)
        return cls


def _organize_validators(configs: List[_ValidatorConfig]) -> Dict[str, Dict[str, List[_ValidatorConfig]]]:
    mapping: Dict[str, Dict[str, List[_ValidatorConfig]]] = {}
    for config in configs:
        for field in config.fields:
            entry = mapping.setdefault(field, {"pre": [], "post": []})
            stage = "pre" if config.pre else "post"
            entry[stage].append(config)
    return mapping


class BaseModel(metaclass=_ModelMeta):
    __fields__: Dict[str, _ModelField]
    __validator_configs__: List[_ValidatorConfig]
    __validators__: Dict[str, Dict[str, List[_ValidatorConfig]]]

    def __init__(self, **data: Any):
        errors: List[Tuple[str, Any]] = []
        values: Dict[str, Any] = {}
        for name, field in self.__fields__.items():
            provided = name in data
            if provided:
                raw_value = data[name]
            else:
                if field.default_factory is not None:
                    raw_value = field.default_factory()
                    provided = False
                elif field.default is not _UNSET:
                    raw_value = field.default
                    provided = False
                else:
                    errors.append((name, "field required"))
                    continue
            try:
                value = self._run_validators(name, raw_value, provided, pre=True)
                value = self._coerce_type(field.type_hint, value)
                value = self._run_validators(name, value, provided, pre=False)
            except ValidationError as exc:  # pragma: no cover - nested aggregation
                nested = [(f"{name}.{err_field}", msg) for err_field, msg in exc.errors()]
                if not nested:
                    nested = [(name, str(exc))]
                errors.extend(nested)
                continue
            except Exception as exc:
                errors.append((name, exc))
                continue
            values[name] = value

        if errors:
            raise ValidationError(errors)

        for key, value in values.items():
            object.__setattr__(self, key, value)

    def dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for name in self.__fields__:
            value = getattr(self, name)
            if isinstance(value, BaseModel):
                result[name] = value.dict()
            elif isinstance(value, list):
                result[name] = [item.dict() if isinstance(item, BaseModel) else item for item in value]
            else:
                result[name] = value
        return result

    @classmethod
    def parse_obj(cls: Type[T], obj: Any) -> T:
        if isinstance(obj, cls):
            return obj
        if not isinstance(obj, Mapping):
            raise ValidationError([(cls.__name__, "input must be a mapping")])
        return cls(**obj)

    @classmethod
    def _run_validators(
        cls,
        name: str,
        value: Any,
        provided: bool,
        *,
        pre: bool,
    ) -> Any:
        entry = cls.__validators__.get(name)
        if not entry:
            return value
        validators = entry["pre" if pre else "post"]
        for config in validators:
            if not provided and not config.always:
                continue
            if config.each_item:
                if not isinstance(value, list):
                    raise TypeError("value must be a list")
                value = [config.func(cls, item) for item in value]
            else:
                value = config.func(cls, value)
        return value

    @classmethod
    def _coerce_type(cls, expected_type: Any, value: Any) -> Any:
        origin = get_origin(expected_type)
        if origin in (list, List):
            item_type = get_args(expected_type)[0] if get_args(expected_type) else Any
            if not isinstance(value, list):
                raise TypeError("value must be a list")
            return [cls._coerce_single(item_type, item) for item in value]
        return cls._coerce_single(expected_type, value)

    @classmethod
    def _coerce_single(cls, expected_type: Any, value: Any) -> Any:
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            last_error: Optional[Exception] = None
            for arg in args:
                if arg is type(None):
                    if value is None:
                        return None
                    continue
                try:
                    return cls._coerce_single(arg, value)
                except Exception as exc:  # pragma: no cover - error path
                    last_error = exc
            if value is None:
                return None
            if last_error is not None:
                raise last_error
            return value
        if expected_type in (Any, object):
            return value
        if isinstance(expected_type, type):
            if issubclass(expected_type, BaseModel):
                if isinstance(value, expected_type):
                    return value
                if isinstance(value, Mapping):
                    return expected_type.parse_obj(value)
                raise TypeError("value must be a mapping")
            if expected_type is str:
                if isinstance(value, str):
                    return value
                raise TypeError("value must be a string")
            if expected_type is int:
                if isinstance(value, int):
                    return value
                raise TypeError("value must be an integer")
            if expected_type is float:
                if isinstance(value, (int, float)):
                    return float(value)
                raise TypeError("value must be a float")
            if expected_type is bool:
                if isinstance(value, bool):
                    return value
                raise TypeError("value must be a boolean")
        return value

    def __setattr__(self, key: str, value: Any) -> None:  # pragma: no cover - immutability safeguard
        raise AttributeError("BaseModel instances are immutable")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        fields = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.__fields__)
        return f"{self.__class__.__name__}({fields})"
