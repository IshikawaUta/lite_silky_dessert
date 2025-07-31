from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import cloudinary
import cloudinary.uploader
import cloudinary.api
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

app = Flask(__name__)
app.config.from_object('config.Config')

# MongoDB Connection
try:
    client = MongoClient(app.config['MONGO_URI'])
    db = client.dessert_ecommerce # Ganti dengan nama database Anda
    # Test connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    # Consider more robust error handling for production

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login' # Redirect to admin login if not logged in
login_manager.login_message_category = 'warning'
bcrypt = Bcrypt(app)

mail = Mail(app)

# Cloudinary Configuration
cloudinary.config(
    cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
    api_key=app.config['CLOUDINARY_API_KEY'],
    api_secret=app.config['CLOUDINARY_API_SECRET']
)

# User Model for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password = user_data['password'] # Hashed password

    @staticmethod
    def get(user_id):
        # Ensure user_id is a valid ObjectId string
        if not ObjectId.is_valid(user_id):
            return None
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            return User(user)
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Initial Admin User Creation (Run this once or during deployment setup) ---
# To create the initial admin user, uncomment the `create_admin_user` route below,
# run the app, navigate to `/admin/setup_initial_admin` once, then comment it back.
# This prevents accidental creation of multiple admin users.

@app.route('/admin/setup_initial_admin')
def setup_initial_admin():
    if db.users.count_documents({}) == 0:
        hashed_password = bcrypt.generate_password_hash("litedessert2025").decode('utf-8')
        db.users.insert_one({'username': 'admin', 'password': hashed_password})
        flash("Default admin user created: username='admin', password='litedessert2025'", 'success')
    else:
        flash("Admin user already exists.", 'info')
    return redirect(url_for('admin_login'))

# --- Context Processor for Base Templates ---
@app.context_processor
def inject_now():
    return {'datetime': datetime}

# --- PUBLIC ROUTES ---

# Home Page
@app.route('/')
def index():
    products = list(db.products.find().limit(4)) # Get 4 latest products
    blog_posts = list(db.blog_posts.find().sort('date_posted', -1).limit(3)) # Get 3 latest blog posts
    return render_template('index.html', products=products, blog_posts=blog_posts)

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    product_results = []
    blog_results = []

    if query:
        # Search in products collection
        product_results = list(db.products.find(
            {'$text': {'$search': query}},
            {'score': {'$meta': 'textScore'}} # Dapatkan skor relevansi
        ).sort([('score', {'$meta': 'textScore'})])) # Urutkan berdasarkan relevansi

        # Search in blog_posts collection
        blog_results = list(db.blog_posts.find(
            {'$text': {'$search': query}},
            {'score': {'$meta': 'textScore'}} # Dapatkan skor relevansi
        ).sort([('score', {'$meta': 'textScore'})])) # Urutkan berdasarkan relevansi

    return render_template('search_results.html',
                           query=query,
                           product_results=product_results,
                           blog_results=blog_results)

# About Us Page
@app.route('/about')
def about():
    return render_template('about.html')

# Contact Page
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message_text = request.form['message']

        # --- LOGIKA PENGIRIMAN EMAIL DENGAN FLASK-MAIL ---
        try:
            msg = Message("Pesan Baru dari Formulir Kontak Lite Dessert",
                          sender=app.config['MAIL_DEFAULT_SENDER'],
                          recipients=["litedessertdrink@gmail.com"])
            msg.body = f"""
Nama Pengirim: {name}
Email Pengirim: {email}
Pesan:
{message_text}
            """
            mail.send(msg)
            flash('Pesan Anda telah terkirim! Kami akan segera menghubungi Anda.', 'success')
        except Exception as e:
            flash(f'Gagal mengirim pesan. Silakan coba lagi nanti. Error: {e}', 'danger')
            print(f"ERROR: Gagal mengirim email: {e}") # Log error untuk debugging
            # Optional: Log the full traceback for more detail
            # import traceback
            # print(traceback.format_exc())

        return redirect(url_for('contact'))
    return render_template('contact.html')

# Products Page
@app.route('/products')
def products():
    all_products = list(db.products.find())
    return render_template('products.html', products=all_products)

# Product Detail Page
@app.route('/product/<id>')
def product_detail(id):
    if not ObjectId.is_valid(id):
        flash('Produk tidak valid.', 'danger')
        return redirect(url_for('products'))
    product = db.products.find_one({'_id': ObjectId(id)})
    if product:
        reviews = list(db.reviews.find({'product_id': ObjectId(id)}).sort('date_posted', -1))
        average_rating = 0
        if reviews:
            total_rating = sum([review['rating'] for review in reviews])
            average_rating = total_rating / len(reviews)
        return render_template('product_detail.html', product=product, reviews=reviews, average_rating=average_rating)
    flash('Produk tidak ditemukan.', 'danger')
    return redirect(url_for('products'))

@app.route('/product/<id>/add_review', methods=['POST'])
def add_review(id):
    if not ObjectId.is_valid(id):
        flash('Produk tidak valid.', 'danger')
        return redirect(url_for('products'))

    product = db.products.find_one({'_id': ObjectId(id)})
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('products'))

    if request.method == 'POST':
        reviewer_name = request.form['reviewer_name']
        rating = int(request.form['rating'])
        comment = request.form['comment']

        if not reviewer_name or not comment or not (1 <= rating <= 5):
            flash('Nama, rating (1-5), dan komentar diperlukan untuk ulasan.', 'danger')
            return redirect(url_for('product_detail', id=id))

        db.reviews.insert_one({
            'product_id': ObjectId(id),
            'reviewer_name': reviewer_name,
            'rating': rating,
            'comment': comment,
            'date_posted': datetime.now()
        })
        flash('Ulasan Anda berhasil ditambahkan!', 'success')
        return redirect(url_for('product_detail', id=id))

# Blog Page
@app.route('/blog')
def blog():
    posts = list(db.blog_posts.find().sort('date_posted', -1))
    return render_template('blog.html', posts=posts)

# Blog Post Detail Page
@app.route('/blog/<id>')
def blog_post(id):
    if not ObjectId.is_valid(id):
        flash('Postingan blog tidak valid.', 'danger')
        return redirect(url_for('blog'))
    post = db.blog_posts.find_one({'_id': ObjectId(id)})
    if post:
        return render_template('blog_post.html', post=post)
    flash('Postingan blog tidak ditemukan.', 'danger')
    return redirect(url_for('blog'))

# Cart Page
@app.route('/cart')
def cart():
    return render_template('cart.html')

# --- ADMIN ROUTES ---

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = db.users.find_one({'username': username})

        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login gagal. Periksa username dan password Anda.', 'danger')
    return render_template('admin/login.html')

# Admin Logout
@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('admin_login'))

# Admin Dashboard
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    total_products = db.products.count_documents({})
    total_blog_posts = db.blog_posts.count_documents({})
    # You might add more stats here, e.g., latest orders if you implement an order system
    return render_template('admin/admin_dashboard.html',
                           total_products=total_products,
                           total_blog_posts=total_blog_posts)

# --- Product Management ---
@app.route('/admin/products')
@login_required
def manage_products():
    products = list(db.products.find())
    return render_template('admin/manage_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        image_file = request.files.get('image') # Use .get() for safety

        image_url = ''
        if image_file and image_file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Gagal mengunggah gambar ke Cloudinary: {e}', 'danger')
                return render_template('admin/add_product.html')

        db.products.insert_one({
            'name': name,
            'description': description,
            'price': price,
            'category': category,
            'image_url': image_url,
            'date_added': datetime.now()
        })
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('manage_products'))
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not ObjectId.is_valid(id):
        flash('Produk tidak valid.', 'danger')
        return redirect(url_for('manage_products'))
    product = db.products.find_one({'_id': ObjectId(id)})
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('manage_products'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        image_file = request.files.get('image')

        image_url = product.get('image_url', '') # Keep existing image if no new one uploaded
        if image_file and image_file.filename != '':
            try:
                # Delete old image from Cloudinary (optional but recommended)
                if image_url:
                    public_id = image_url.split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(public_id)
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Gagal mengunggah gambar ke Cloudinary: {e}', 'danger')
                return render_template('admin/edit_product.html', product=product)

        db.products.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'name': name,
                'description': description,
                'price': price,
                'category': category,
                'image_url': image_url,
                'last_updated': datetime.now()
            }}
        )
        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('manage_products'))
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/products/delete/<id>', methods=['POST'])
@login_required
def delete_product(id):
    if not ObjectId.is_valid(id):
        flash('Produk tidak valid.', 'danger')
        return redirect(url_for('manage_products'))
    product = db.products.find_one({'_id': ObjectId(id)})
    if product:
        if product.get('image_url'):
            try:
                public_id = product['image_url'].split('/')[-1].split('.')[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Error deleting image from Cloudinary: {e}") # Log error, but proceed with DB delete
        db.products.delete_one({'_id': ObjectId(id)})
        flash('Produk berhasil dihapus!', 'success')
    else:
        flash('Produk tidak ditemukan.', 'danger')
    return redirect(url_for('manage_products'))

# --- Blog Management ---
@app.route('/admin/blog')
@login_required
def manage_blog():
    posts = list(db.blog_posts.find().sort('date_posted', -1))
    return render_template('admin/manage_blog.html', posts=posts)

@app.route('/admin/blog/add', methods=['GET', 'POST'])
@login_required
def add_blog_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form.get('author', current_user.username) # Default to logged-in user
        image_file = request.files.get('image')

        image_url = ''
        if image_file and image_file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Gagal mengunggah gambar ke Cloudinary: {e}', 'danger')
                return render_template('admin/add_blog_post.html')

        db.blog_posts.insert_one({
            'title': title,
            'content': content,
            'author': author,
            'image_url': image_url,
            'date_posted': datetime.now()
        })
        flash('Postingan blog berhasil ditambahkan!', 'success')
        return redirect(url_for('manage_blog'))
    return render_template('admin/add_blog_post.html')

@app.route('/admin/blog/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_blog_post(id):
    if not ObjectId.is_valid(id):
        flash('Postingan blog tidak valid.', 'danger')
        return redirect(url_for('manage_blog'))
    post = db.blog_posts.find_one({'_id': ObjectId(id)})
    if not post:
        flash('Postingan blog tidak ditemukan.', 'danger')
        return redirect(url_for('manage_blog'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_file = request.files.get('image')

        image_url = post.get('image_url', '')
        if image_file and image_file.filename != '':
            try:
                if image_url:
                    public_id = image_url.split('/')[-1].split('.')[0]
                    cloudinary.uploader.destroy(public_id)
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Gagal mengunggah gambar ke Cloudinary: {e}', 'danger')
                return render_template('admin/edit_blog_post.html', post=post)

        db.blog_posts.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'title': title,
                'content': content,
                'image_url': image_url,
                'last_updated': datetime.now()
            }}
        )
        flash('Postingan blog berhasil diperbarui!', 'success')
        return redirect(url_for('manage_blog'))
    return render_template('admin/edit_blog_post.html', post=post)

@app.route('/admin/blog/delete/<id>', methods=['POST'])
@login_required
def delete_blog_post(id):
    if not ObjectId.is_valid(id):
        flash('Postingan blog tidak valid.', 'danger')
        return redirect(url_for('manage_blog'))
    post = db.blog_posts.find_one({'_id': ObjectId(id)})
    if post:
        if post.get('image_url'):
            try:
                public_id = post['image_url'].split('/')[-1].split('.')[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Error deleting image from Cloudinary: {e}")
        db.blog_posts.delete_one({'_id': ObjectId(id)})
        flash('Postingan blog berhasil dihapus!', 'success')
    else:
        flash('Postingan blog tidak ditemukan.', 'danger')
    return redirect(url_for('manage_blog'))

@app.route('/sitemap.xml')
def sitemap():
    # Buat daftar URL statis dan dinamis
    urls = []
    
    # URL statis
    static_urls = ['index', 'products', 'blog', 'about', 'contact', 'admin_login']
    for url in static_urls:
        urls.append({
            'loc': url_for(url, _external=True),
            'lastmod': datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'),
            'changefreq': 'daily' if url in ['index', 'products'] else 'monthly',
            'priority': '1.0' if url == 'index' else '0.8'
        })
    
    # URL dinamis (Produk)
    products = list(db.products.find({}, {'_id': 1, 'last_updated': 1}))
    for product in products:
        lastmod = product.get('last_updated', datetime.now())
        urls.append({
            'loc': url_for('product_detail', id=product['_id'], _external=True),
            'lastmod': lastmod.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'changefreq': 'weekly',
            'priority': '0.7'
        })

    # URL dinamis (Blog)
    blog_posts = list(db.blog_posts.find({}, {'_id': 1, 'date_posted': 1}))
    for post in blog_posts:
        lastmod = post.get('date_posted', datetime.now())
        urls.append({
            'loc': url_for('blog_post', id=post['_id'], _external=True),
            'lastmod': lastmod.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'changefreq': 'weekly',
            'priority': '0.6'
        })
    
    xml_content = render_template('sitemap.xml', urls=urls)
    response = Response(xml_content, mimetype='application/xml')
    return response

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory('static', 'robots.txt')


if __name__ == '__main__':
    app.run(debug=True) # Set debug=False in production