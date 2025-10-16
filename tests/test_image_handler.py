from src.assistant.image_handler import format_image_urls_for_openai

def test_format_image_urls():
    urls = ["https://www.dropbox.com/scl/fi/t47b2ub9kd4a1vkh03unf/Icfes_unalOdyssey.jpg?rlkey=hiqhjvlyn0855vwh7gqex0yzn&st=odvx96yu&raw=1", "https://www.dropbox.com/scl/fi/hy9vlwecqe2scv4rgbmnd/claseGratisUnal.jpg?rlkey=7flhwlyoqvo3z8h5iks2vlg5u&st=w22dcux1&raw=1"]
    result = format_image_urls_for_openai(urls)

    assert len(result) == 2
    assert result[0]["type"] == "input_image"
    assert result[0]["input_image"]["url"] == urls[0]
    print("✅ Formatted image content:", result)

# This makes it executable directly:
if __name__ == "__main__":
    test_format_image_urls()
