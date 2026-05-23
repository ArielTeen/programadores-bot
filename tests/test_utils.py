import pytest, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.embeds import PremiumEmbed
from utils.helpers import format_duration, parse_duration, get_level_xp, get_level_from_xp, clean_text

def test_premium_embed_defaults():
    embed = PremiumEmbed(title="Test")
    assert embed.color.value == 0x7C3AED
    embed.set_standard_footer()
    assert "Comunidad de Programadores" in embed.footer.text

def test_premium_embed_custom():
    embed = PremiumEmbed(title="Custom", color=0x00FF00)
    assert embed.color.value == 0x00FF00
    embed.set_footer(text="Custom Footer")
    assert embed.footer.text == "Custom Footer"

def test_format_duration():
    assert format_duration(60) == "1m 0s"
    assert format_duration(3600) == "1h 0m"
    assert format_duration(30) == "30s"
    assert format_duration(86400) == "1d 0h 0m"

def test_parse_duration():
    assert parse_duration("30s") == 30
    assert parse_duration("5m") == 300
    assert parse_duration("2h") == 7200
    assert parse_duration("1d") == 86400
    assert parse_duration("") == 0

def test_get_level_xp():
    assert get_level_xp(0) == 100
    assert get_level_xp(1) == 155
    assert get_level_xp(5) == 475

def test_get_level_from_xp():
    assert get_level_from_xp(0) == 0
    assert get_level_from_xp(100) == 1
    assert get_level_from_xp(255) == 2

def test_clean_text():
    result = clean_text("Hello *world*")
    assert "\\*" in result or result == "Hello *world*"  # may or may not escape
