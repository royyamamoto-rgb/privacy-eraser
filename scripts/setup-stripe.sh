#!/bin/bash

# Privacy Eraser - Stripe Product Setup Script
# Run this script with your Stripe secret key to create products and prices

if [ -z "$1" ]; then
    echo "Usage: ./setup-stripe.sh sk_test_your_secret_key"
    echo ""
    echo "Get your secret key from: https://dashboard.stripe.com/apikeys"
    exit 1
fi

STRIPE_KEY=$1
API="https://api.stripe.com/v1"

echo "Creating Stripe products for Privacy Eraser..."
echo ""

# Create Basic Plan Product
echo "Creating Basic Plan product..."
BASIC_PRODUCT=$(curl -s -X POST "$API/products" \
    -u "$STRIPE_KEY:" \
    -d "name=Privacy Eraser Basic" \
    -d "description=50 broker scans, auto-removal, email support" \
    -d "metadata[plan]=basic")

BASIC_PRODUCT_ID=$(echo $BASIC_PRODUCT | grep -o '"id":"prod_[^"]*"' | cut -d'"' -f4)
echo "  Product ID: $BASIC_PRODUCT_ID"

# Create Basic Plan Price ($5/month)
echo "Creating Basic Plan price ($5/month)..."
BASIC_PRICE=$(curl -s -X POST "$API/prices" \
    -u "$STRIPE_KEY:" \
    -d "product=$BASIC_PRODUCT_ID" \
    -d "unit_amount=500" \
    -d "currency=usd" \
    -d "recurring[interval]=month" \
    -d "metadata[plan]=basic")

BASIC_PRICE_ID=$(echo $BASIC_PRICE | grep -o '"id":"price_[^"]*"' | cut -d'"' -f4)
echo "  Price ID: $BASIC_PRICE_ID"
echo ""

# Create Premium Plan Product
echo "Creating Premium Plan product..."
PREMIUM_PRODUCT=$(curl -s -X POST "$API/products" \
    -u "$STRIPE_KEY:" \
    -d "name=Privacy Eraser Premium" \
    -d "description=Unlimited scans, priority removal, monitoring alerts" \
    -d "metadata[plan]=premium")

PREMIUM_PRODUCT_ID=$(echo $PREMIUM_PRODUCT | grep -o '"id":"prod_[^"]*"' | cut -d'"' -f4)
echo "  Product ID: $PREMIUM_PRODUCT_ID"

# Create Premium Plan Price ($9/month)
echo "Creating Premium Plan price ($9/month)..."
PREMIUM_PRICE=$(curl -s -X POST "$API/prices" \
    -u "$STRIPE_KEY:" \
    -d "product=$PREMIUM_PRODUCT_ID" \
    -d "unit_amount=900" \
    -d "currency=usd" \
    -d "recurring[interval]=month" \
    -d "metadata[plan]=premium")

PREMIUM_PRICE_ID=$(echo $PREMIUM_PRICE | grep -o '"id":"price_[^"]*"' | cut -d'"' -f4)
echo "  Price ID: $PREMIUM_PRICE_ID"
echo ""

echo "============================================"
echo "Stripe products created successfully!"
echo "============================================"
echo ""
echo "Add these to your environment variables:"
echo ""
echo "STRIPE_SECRET_KEY=$STRIPE_KEY"
echo "STRIPE_PRICE_BASIC=$BASIC_PRICE_ID"
echo "STRIPE_PRICE_PREMIUM=$PREMIUM_PRICE_ID"
echo ""
echo "For webhooks, create one at:"
echo "https://dashboard.stripe.com/webhooks"
echo ""
echo "Webhook URL: https://your-api-domain.com/api/billing/webhook"
echo "Events to listen for:"
echo "  - checkout.session.completed"
echo "  - customer.subscription.updated"
echo "  - customer.subscription.deleted"
