from typing import Dict, Type, Any, Optional
from channels.base import BaseChannel

class ChannelFactory:
    _registry: Dict[str, Type[BaseChannel]] = {}

    @classmethod
    def register(cls, name: str, channel_class: Type[BaseChannel]):
        cls._registry[name.lower()] = channel_class

    @classmethod
    def get_channel_class(cls, name: str) -> Optional[Type[BaseChannel]]:
        return cls._registry.get(name.lower())

    @classmethod
    def create_instance(cls, name: str, **kwargs) -> BaseChannel:
        channel_class = cls.get_channel_class(name)
        if not channel_class:
            raise ValueError(f"Channel '{name}' is not registered.")
        return channel_class(**kwargs)

# Pre-register known channels
from channels.line.driver import LineChannel
ChannelFactory.register("line", LineChannel)
