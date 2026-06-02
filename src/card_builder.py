"""Feishu message card builder.

Uses the lark-oapi SDK's built-in CardBuilder to turn LLM reply text into
CardKit v2 card payloads (colored header + markdown body).
"""

from lark_oapi.channel.card.builder import new_card

from src.config import BOT_DISPLAY_NAME


def build_reply_card(text: str, *, title: str | None = None, color: str = "blue") -> dict:
    """Convert reply text into a Feishu card payload.

    Args:
        text: Reply text (supports lark_md formatting).
        title: Card header title. Defaults to BOT_DISPLAY_NAME.
        color: Header color template (blue, green, red, etc.).

    Returns:
        CardKit v2 dict, ready for channel.send(chat_id, {"card": payload}).
    """
    card = new_card()
    card.config(wide_screen_mode=True)
    card.header(title=title or BOT_DISPLAY_NAME, template=color)
    card.markdown(content=text)
    return card.build().data


def build_confirm_card(
    text: str,
    tool_name: str,
    action_id: str,
    confirm_label: str = "确认",
    cancel_label: str = "取消",
) -> dict:
    """Card with confirm/cancel buttons for protected write operations.

    Each button's value embeds the action_id for callback matching.
    """
    card = new_card()
    card.config(wide_screen_mode=True)
    card.header(title="Action Confirmation", template="blue")
    card.markdown(content=text)
    card.divider()
    card.button(
        label=confirm_label,
        action={"type": "button", "value": {"action_id": action_id, "type": "confirm", "tool": tool_name}},
        style="primary",
    )
    card.button(
        label=cancel_label,
        action={"type": "button", "value": {"action_id": action_id, "type": "cancel", "tool": tool_name}},
        style="default",
    )
    return card.build().data


def build_error_card(error_text: str) -> dict:
    """Error card with red header."""
    card = new_card()
    card.config(wide_screen_mode=True)
    card.header(title="Error", template="red")
    card.markdown(content=error_text)
    return card.build().data
