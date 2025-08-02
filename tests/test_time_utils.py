from src.utils.time_utils import get_current_time_info

def test_get_current_time_info():
    result = get_current_time_info()

    assert "iso" in result
    assert "date" in result
    assert "time" in result
    assert "day" in result
    assert "full_human" in result
    print("✅ Time info:", result)

# This makes it executable directly:
if __name__ == "__main__":
    test_get_current_time_info()
