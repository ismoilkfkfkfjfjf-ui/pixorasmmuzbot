import re
import aiohttp

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class ProfileDownloader:
    """Utility to download profile picture (avatar HD) and extract bio details for Instagram and Telegram."""
    
    @staticmethod
    def clean_username(input_text: str) -> tuple[str, str]:
        """Returns (platform, username). Platform is 'instagram' or 'telegram'."""
        text = input_text.strip()
        if "instagram.com" in text:
            # e.g. https://instagram.com/username
            match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]+)", text)
            if match:
                return "instagram", match.group(1).rstrip("/")
        if "t.me" in text or "telegram.me" in text:
            match = re.search(r"(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)", text)
            if match:
                return "telegram", match.group(1).rstrip("/")
        
        # If bare username like @username
        username = text.lstrip("@").strip()
        return "auto", username

    @staticmethod
    async def get_telegram_profile(username: str) -> dict:
        """Fetches public Telegram profile photo, title, bio, members."""
        url = f"https://t.me/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return {"error": f"Profil topilmadi (Status: {resp.status})"}
                    html = await resp.text()

                    # Extract avatar
                    avatar_match = re.search(r'class="tgme_page_photo_image"\s+src="([^"]+)"', html)
                    avatar_url = avatar_match.group(1) if avatar_match else None

                    # Extract title
                    title_match = re.search(r'<div class="tgme_page_title"[^>]*><span[^>]*>(.*?)</span>', html, re.DOTALL)
                    if not title_match:
                        title_match = re.search(r'<div class="tgme_page_title"[^>]*>(.*?)</div>', html, re.DOTALL)
                    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else username

                    # Extract bio / description
                    desc_match = re.search(r'<div class="tgme_page_description"[^>]*>(.*?)</div>', html, re.DOTALL)
                    bio = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else "Bio mavjud emas"

                    # Extract extra (subscribers/members)
                    extra_match = re.search(r'<div class="tgme_page_extra"[^>]*>(.*?)</div>', html, re.DOTALL)
                    extra = extra_match.group(1).strip() if extra_match else ""

                    return {
                        "platform": "Telegram",
                        "username": f"@{username}",
                        "title": title,
                        "bio": bio,
                        "extra": extra,
                        "avatar_url": avatar_url,
                        "profile_url": url
                    }
        except Exception as e:
            return {"error": f"Telegram ma'lumotlarini olishda xatolik: {str(e)}"}

    @staticmethod
    async def get_instagram_profile(username: str) -> dict:
        """Fetches public Instagram profile photo and bio."""
        url = f"https://www.instagram.com/{username}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    html = await resp.text()

                    # Try OpenGraph tags
                    og_image = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', html)

                    avatar_url = og_image.group(1) if og_image else None
                    title = og_title.group(1) if og_title else f"@{username}"
                    bio = og_desc.group(1) if og_desc else "Bio olinmadi yoki profil yopiq"

                    return {
                        "platform": "Instagram",
                        "username": f"@{username}",
                        "title": title,
                        "bio": bio,
                        "avatar_url": avatar_url,
                        "profile_url": url
                    }
        except Exception as e:
            return {"error": f"Instagram ma'lumotlarini olishda xatolik: {str(e)}"}

profile_downloader = ProfileDownloader()
