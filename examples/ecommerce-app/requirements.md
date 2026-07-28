# E-Commerce Platform Requirements

## Project Overview

Build a full-featured e-commerce platform that allows users to browse products, manage shopping carts, place orders, and process payments. The platform includes an admin dashboard for product and order management, inventory tracking, and customer management.

## Target Users

- **Customers**: Browse products, make purchases, track orders
- **Administrators**: Manage products, inventory, orders, and customers
- **Guest Users**: Browse products without authentication (limited features)

## Functional Requirements

### 1. User Authentication & Management

**User Registration:**
- Email, password, first name, last name
- Email verification (simulated)
- Password requirements: min 8 chars, 1 uppercase, 1 number, 1 special character
- Default role: "customer"
- Store registration date and last login

**User Login:**
- Email and password authentication
- JWT token (expires in 7 days)
- "Remember me" option (30-day token)
- Failed attempt tracking (lock after 5 failures, 15-minute cooldown)

**User Profile:**
- Personal information (name, email, phone)
- Shipping addresses (multiple, mark default)
- Order history
- Saved payment methods (tokenized, not storing real cards)
- Profile picture upload


**User Roles:**
- Customer: Browse, purchase, manage own orders
- Admin: All customer permissions + product/inventory/order management

### 2. Product Catalog

**Product Management:**
- Product fields:
  - Name (required, max 200 chars)
  - SKU (required, unique, auto-generated)
  - Description (required, max 5000 chars, markdown supported)
  - Short description (max 300 chars)
  - Price (required, decimal, min 0.01)
  - Sale price (optional, must be less than price)
  - Category (required, select from predefined)
  - Brand (optional)
  - Images (multiple, up to 5 per product)
  - Stock quantity (required, integer, min 0)
  - Weight (optional, for shipping)
  - Dimensions (optional: length, width, height)
  - Status (draft, active, discontinued)
  - Featured (boolean, for homepage display)
  - Created date, updated date
  - Average rating (calculated from reviews)
  - Total reviews count

**Categories:**
- Hierarchical structure (parent-child relationships)
- Category fields: name, slug, description, parent_id, image
- Display products by category
- Category navigation/breadcrumbs

**Product Images:**
- Primary image (first uploaded)
- Additional images (gallery)
- Supported formats: JPEG, PNG, WebP
- Max file size: 5 MB per image
- Auto-resize to multiple sizes (thumbnail, medium, large)

**Inventory Management:**
- Track stock quantity per product
- Low stock threshold (configurable, default 10)
- Low stock alerts for admins
- Out of stock indicator
- Stock history (increases/decreases with timestamps)
- Allow backorders option (boolean per product)


### 3. Shopping Cart

**Cart Management:**
- Guest users can add to cart (session-based, converts on login)
- Authenticated users have persistent carts
- Cart items:
  - Product reference
  - Quantity (min 1, max based on stock)
  - Price snapshot (at time of adding)
  - Subtotal (quantity × price)
- Add to cart
- Update quantity
- Remove from cart
- Clear cart
- Cart persists across sessions for authenticated users
- Calculate totals: subtotal, tax, shipping, total

**Cart Rules:**
- Cannot add out-of-stock items
- Quantity limited by available stock
- If stock decreases below cart quantity, show warning
- Price updates reflect current product price (not cart snapshot) at checkout

### 4. Checkout & Orders

**Checkout Process:**
1. Cart review (items, quantities, prices)
2. Shipping address (select saved or add new)
3. Shipping method selection (standard, express, overnight)
4. Payment method (credit card mock, Stripe integration simulated)
5. Order review and confirmation
6. Order placement

**Order Creation:**
- Order fields:
  - Order number (auto-generated, unique, format: ORD-YYYYMMDD-XXXX)
  - User reference
  - Order items (product, quantity, price, subtotal)
  - Shipping address snapshot
  - Shipping method and cost
  - Subtotal
  - Tax amount (calculated at 8%)
  - Total amount
  - Payment method
  - Payment status (pending, paid, failed, refunded)
  - Order status (pending, processing, shipped, delivered, cancelled)
  - Notes (optional, from customer)
  - Admin notes (optional, internal)
  - Created date, updated date, shipped date, delivered date

**Order Status Flow:**
- pending → processing → shipped → delivered
- Can cancel if status is pending or processing
- Email notifications on status changes (simulated, logged to console)

**Order Management (Customer):**
- View order history (paginated)
- View order details
- Cancel order (if eligible)
- Track shipment (mock tracking number)
- Request refund (creates support ticket, not automatic)

**Order Management (Admin):**
- View all orders (filterable by status, date, customer)
- Update order status
- Add tracking information
- Process refunds
- Add admin notes
- Export order data (CSV)

