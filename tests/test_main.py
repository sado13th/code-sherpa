"""Test main module."""

from code_sherpa.main import main


def test_main(capsys):
    """Test main function."""
    main()
    captured = capsys.readouterr()
    assert "Hello" in captured.out
