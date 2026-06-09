from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from tktop.config import Config


class ProviderPickerScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ProviderPickerScreen {
        align: center middle;
    }

    #picker-container {
        width: 50;
        height: 12;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config

    def compose(self) -> ComposeResult:
        providers = [
            ("ollama", self.config.ollama_model),
            ("anthropic", self.config.anthropic_model),
            ("vertex", self.config.vertex_model),
            ("openai", self.config.openai_model),
        ]

        options = []
        for name, model in providers:
            marker = " ●" if name == self.config.llm_provider else "  "
            options.append(Option(f"{marker} {name:<12} {model}", id=name))

        yield Vertical(
            Label(" Select LLM Provider"),
            OptionList(*options, id="provider-list"),
            id="picker-container",
        )

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(str(event.option_id))

    def action_cancel(self) -> None:
        self.dismiss(None)
