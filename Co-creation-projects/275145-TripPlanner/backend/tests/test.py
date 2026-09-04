
from app.services.unsplash_service import UnsplashService

if __name__ == "__main__":
    service = UnsplashService(access_key="qoRz2cAQwJD5kPyrN7_2dqdn_1Kfp-DXq4TQKK_dgI8")
    photos = service.search_photos("beijing", per_page=1)
    print(photos)