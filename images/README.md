# FlipTrack AI - Client Branding

## 📁 Folder Structure

```
images/
└── [client_name]/
    ├── logo.svg              # Full logo with text
    ├── logo_icon.svg         # Icon only (no text)
    ├── logo_white.svg        # White version for dark backgrounds
    └── brand_colors.json     # Brand colors and contact info
```

## 🎨 Kituwah Properties Branding

### Colors
- **Primary Red:** #D32F2F
- **Dark Red:** #B71C1C
- **Roof Red:** #E53935
- **Text Dark:** #4E342E
- **Cream:** #F5F5DC
- **Accent Green:** #81C784

### Assets
- `logo.svg` - Full business card style logo
- `logo_icon.svg` - House icon only (160x160)
- `logo_white.svg` - For dark backgrounds
- `brand_colors.json` - All brand data

### Contact Info
- **Owner:** Steve Griggs
- **Phone:** 214.293.2398
- **Email:** sg.krupkinlaw@gmail.com
- **Tagline:** "We buy & sell houses"

## 🚀 Adding New Clients

1. Create folder: `images/[client_name]/`
2. Add logo files (SVG format recommended)
3. Create `brand_colors.json` with:
   ```json
   {
     "company": "Client Name",
     "colors": {
       "primary": "#HEX",
       "secondary": "#HEX"
     },
     "contact": {
       "owner": "Name",
       "phone": "XXX-XXX-XXXX"
     }
   }
   ```

## 💡 Usage in App

```python
# Load client branding
import json

client_name = "kituwah_properties"
with open(f"images/{client_name}/brand_colors.json") as f:
    brand = json.load(f)

# Use in Streamlit
st.image(f"images/{client_name}/logo.svg")
st.markdown(f"<h1 style='color: {brand['colors']['primary_red']}'>{brand['company']}</h1>")
```

## 🎯 Multi-Tenant Ready

Each client gets their own branded experience:
- Custom logo in header
- Custom color scheme
- Custom contact info
- Separate database (already implemented)
