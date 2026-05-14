## Swiggy Intent Search
A prototype that fixes Swiggy's search for natural-language queries like "filling lunch under 250" or "biryani not too spicy."

**Live demo:** https://swiggy-intent-search.streamlit.app

<img width="1920" height="1080" alt="Screenshot 2026-05-14 at 2 16 46 PM" src="https://github.com/user-attachments/assets/f1da0487-1766-4784-a64a-c64b6a54facc" />

### What it does
Swiggy's current search treats queries as keyword strings, which means anything beyond a single dish name fails. This prototype shows what intent-aware search could look like instead.
When you type a query, the system:

Extracts structured filters using an LLM (cuisine, meal type, price, dietary, spice level, portion size, etc.)
Shows what it understood in a transparent panel, so you can see and correct the interpretation
Flags terms it couldn't map, instead of silently dropping them
Returns matching items from a mock catalogue of 150 dishes

### Tech

- Streamlit for the UI
- Groq + Llama 3.3 70B for filter extraction
- Claude Code for the build

### Running locally
```bash 
git clone https://github.com/aarushimaurya/swiggy-intent-search
cd swiggy-intent-search
pip install -r requirements.txt
```
Create a .env file with your Groq API key:
```
GROQ_API_KEY=your_key_here
```
Then run:
```bash
streamlit run app.py
```
**Note**: First load on the live demo may take 10-30 seconds as the free Streamlit Cloud server wakes up
