from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseChannel(ABC):
    """
    Abstract interface for a communication channel (LINE, Messenger, Taobao, etc.)
    Allows the AI Engine to interact with different platforms without knowing implementation details.
    """
    
    @abstractmethod
    async def select_chat(self, chat_name: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to and open a specific chat."""
        pass

    @abstractmethod
    async def extract_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch message history from the currently active chat."""
        pass

    @abstractmethod
    async def send_message(self, text: str) -> bool:
        """Send a text message to the currently active chat."""
        pass

    @abstractmethod
    async def send_image(self, image_path: str) -> bool:
        """Send an image to the currently active chat."""
        pass

    @abstractmethod
    async def bring_to_front(self) -> None:
        """Ensure the channel interface is visible and active."""
        pass
