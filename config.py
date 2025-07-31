import os

class Config:
    # key yang kompleks dan unik
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_change_me_in_production'
    
    # MongoDB Atlas Connection String
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb+srv://user:password@cluster.mongodb.net/mydatabase?retryWrites=true&w=majority'
    
    # Cloudinary Credentials
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME') or 'your_cloudinary_cloud_name'
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY') or 'your_cloudinary_api_key'
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET') or 'your_cloudinary_api_secret'
    
    # Flask-Mail (fitur kontak email/notifikasi)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
    MAIL_DEFAULT_SENDER = os.environ.get('EMAIL_USER')