# OnboardIQ Demo Recording Script

## Setup
1. Ensure all services running: `docker compose up`
2. Ensure Stripe docs ingested: `make ingest`
3. Open browser to http://localhost:3000
4. Resize window to 1440x900 (or similar 16:10)
5. Use a screen recorder: Kap (Mac), ScreenToGif (Windows), OBS + ffmpeg

## Recording Steps

### Scene 1: Product Selection (2 seconds)
- Show the landing page with product cards
- Click on "Stripe"

### Scene 2: Role Configuration (4 seconds)
- Click "Security Engineer" role card
- Set experience to "Intermediate"
- Add focus area: "API security" (type and press Enter)
- Set tech stack: "Python"
- Click "Generate Guide"

### Scene 3: Pipeline Progress (8 seconds)
- Show the pipeline stepper animating through each agent
- Let 2-3 sections stream in with their summaries
- Show quality badges appearing on sections
- (If regeneration triggers, great — show that too)

### Scene 4: Complete Guide (6 seconds)
- Show the full GuideViewer
- Click through 2-3 sections in the sidebar
- Hover over a citation to show the tooltip
- Pan to the radar chart showing evaluation scores
- Briefly show the metadata panel (tokens, cost, latency)

### Total: ~20 seconds

## Best Demo Configurations
| Product | Role | Experience | Why it demos well |
|---------|------|-----------|-------------------|
| Stripe | Security Engineer | Intermediate | Rich role-specific content, good eval scores |
| Stripe | Backend Developer | Beginner | Different output for same docs, visible adaptation |
| Stripe | Frontend Developer | Advanced | Shows tech stack customization |

## Post-Processing
- Trim to under 30 seconds
- Convert to GIF: `ffmpeg -i demo.mp4 -vf "fps=12,scale=720:-1" docs/assets/demo.gif`
- Target file size: under 5MB
- Place in: `docs/assets/demo.gif`
