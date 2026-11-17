# DREAMSADVERSTINGS — Premium OOH & DOOH Advertising Marketplace

Headquartered in **Pune, Maharashtra, India**, **DreamsAdverstings** is a full-stack Outdoor (OOH) and Digital Out-of-Home (DOOH) advertising marketplace connecting advertisers, media buyers, verified outdoor media owners, and agency operations teams.

## Key Capabilities
- **156 Real Pune Seed Inventory Listings**: Pre-loaded from `Marquis_Pune_Inventory__List-_03.10.2026.xlsx` (clearly marked as `[DEMO DATA]`) with exact GPS coordinates, dimensions, illumination types (`FL`, `NL`, `BL`, `LED`), monthly display costs (`₹75,000`–`₹1,800,000`), and availability dates across 18+ Pune corridors.
- **11 Public Marketplace Pages**: Home, About Us, Services (16 categories), Media Inventory Marketplace (Grid/List + Compare), Media Details, Explore Locations (Interactive Map), Portfolio, Case Studies, Our Clients, Media Planning, and Contact Us.
- **3 Role-Isolated Business Portals**: Customer Portal, Vendor / Media Owner Portal (with verification gate), and 22-Module Admin Portal.
- **Transactional Booking & Pricing Engine**: Prevents overlapping bookings, enforces 15-minute payment holds, computes backend-authoritative quotations (with Installation, Printing, Commission, and 18% GST), and verifies Razorpay Test Mode signatures server-side.
- **Grounded AI Media Planner**: Recommends approved Pune inventory matching campaign budget, corridor, and format criteria.

## Quick Start (Docker Compose)
```bash
cp .env.example .env
docker compose up --build
```
- **Frontend**: `http://localhost:3000`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`

## Running Backend Unit & Integration Tests
```bash
cd backend
pytest -v
```
