// Function to update cart count in the navbar
function updateCartCount() {
    const cart = JSON.parse(localStorage.getItem('cart')) || [];
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    document.getElementById('cart-count').innerText = count;
    const offcanvasCartCount = document.getElementById('cart-count-offcanvas');
    if (offcanvasCartCount) {
        offcanvasCartCount.innerText = count;
    }
}

// Function to add a product to the cart
function addToCart(productId, productName, productPrice, productImage) {
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    const existingItemIndex = cart.findIndex(item => item.id === productId);

    if (existingItemIndex > -1) {
        cart[existingItemIndex].quantity += 1;
    } else {
        cart.push({
            id: productId,
            name: productName,
            price: productPrice,
            image: productImage,
            quantity: 1
        });
    }

    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
    UIkit.notification({
        message: '<span uk-icon="icon: check"></span> Produk berhasil ditambahkan ke keranjang!',
        status: 'success',
        pos: 'top-right',
        timeout: 2000
    });
}

// Event listener for 'Add to Cart' buttons dynamically
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('add-to-cart-btn')) {
        // Prevent default button action (e.g., form submission if it's a form button)
        event.preventDefault();

        const productId = event.target.dataset.id;
        const productName = event.target.dataset.name;
        const productPrice = parseFloat(event.target.dataset.price);
        const productImage = event.target.dataset.image;

        addToCart(productId, productName, productPrice, productImage);
    }
});

// For smooth scrolling (optional, but good for UX)
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();

        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});
// Pastikan DOM sudah dimuat sebelum menjalankan script
document.addEventListener('DOMContentLoaded', function() {
    // Cari elemen dropdown pencarian
    var searchDropdown = document.querySelector('.uk-navbar-dropdown[uk-dropdown]');

    // Pastikan elemen ditemukan
    if (searchDropdown) {
        // Tambahkan event listener saat dropdown dibuka
        UIkit.util.on(searchDropdown, 'show', function () {
            // Ketika dropdown dibuka, cari input di dalamnya dan beri fokus
            var searchInput = this.querySelector('.uk-search-input');
            if (searchInput) {
                searchInput.focus();
            }
        });
    }
});