"""Small visual system for the Streamlit product shell."""

APP_CSS = """
<style>
  .stApp { background: #f7f8fa; }
  [data-testid="stSidebar"] { background: #101828; }
  [data-testid="stSidebar"] * { color: #f8fafc; }
  .resume-hero {
    padding: 1.4rem 1.6rem;
    border-radius: 18px;
    background: linear-gradient(125deg, #0f3d5e, #116466);
    color: white;
    margin-bottom: 1rem;
  }
  .resume-hero h2 { margin: 0 0 .35rem 0; }
  .resume-eyebrow { letter-spacing: .08em; text-transform: uppercase; opacity: .75; }
  .evidence-chip {
    display: inline-block; margin: .15rem .25rem .15rem 0; padding: .18rem .55rem;
    background: #e6f4f1; color: #115e59; border-radius: 999px; font-size: .8rem;
  }
  .muted-card {
    border: 1px solid #d0d5dd; border-radius: 14px; padding: 1rem; background: white;
  }
</style>
"""
