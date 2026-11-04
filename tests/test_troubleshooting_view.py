"""Unit tests for troubleshooting view and error resolution components."""

from unittest.mock import MagicMock, patch
import pytest

from ui.troubleshooting_view import _open_game_folder_in_explorer, render_troubleshooting_view


def test_troubleshooting_view_renders_cleanly(monkeypatch):
    """Verify render_troubleshooting_view runs with all containers, info cards and buttons."""
    mock_st = MagicMock()
    mock_st.session_state = {"active_nav": "troubleshooting"}
    mock_st.container.return_value.__enter__.return_value = MagicMock()
    mock_st.expander.return_value.__enter__.return_value = MagicMock()
    mock_st.columns.return_value = [MagicMock(), MagicMock()]
    mock_st.button.return_value = False

    monkeypatch.setattr("ui.troubleshooting_view.st", mock_st)

    render_troubleshooting_view()
    assert mock_st.markdown.called
    assert mock_st.container.called
    assert mock_st.code.called


def test_open_game_folder_in_explorer_on_windows(monkeypatch):
    """Verify _open_game_folder_in_explorer executes system explorer on win32."""
    monkeypatch.setattr("sys.platform", "win32")
    with patch("os.startfile", create=True) as mock_startfile, \
         patch("ui.troubleshooting_view.get_game_imported_songs_dir") as mock_dir:
        mock_path = MagicMock()
        mock_dir.return_value = mock_path
        res = _open_game_folder_in_explorer()
        assert res is True
        mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_startfile.assert_called_once_with(str(mock_path))


def test_open_game_folder_in_explorer_non_windows(monkeypatch):
    """Verify _open_game_folder_in_explorer gracefully returns False on non-windows."""
    monkeypatch.setattr("sys.platform", "linux")
    res = _open_game_folder_in_explorer()
    assert res is False
