import pandas as pd
from groq import Groq
import os
from datetime import datetime

df = pd.read_csv("leads.csv")
print(f"found {len(df)} leads\n")
print(df)

client = Groq(api_key= os.environ.get("GROQ_API_KEY"))
def score_lead(last_contact_str):
    last_contact = datetime.strptime(last_contact_str, "%Y-%m-%d")
    #how many days since last contacted?
    days_ago = (datetime.now() - last_contact).days

    # score based on how long ago
    if days_ago <=90:
        return "Warm", days_ago 
    elif days_ago <= 180:
        return "Hot", days_ago 
    else:
        return "Cold", days_ago


def generate_message(name, property_interest, location, score, days_ago):

    prompt = f"""
You are a friendly real estate broker assistant.
Write a short, warm reactivation text message to a lead.

Lead details:
- Name: {name}
- They were interested in: {property_interest}
- Location: {location}
- Last contacted: {days_ago} days ago
- Priority score: {score}

Rules:
- Maximum 3 sentences
- Sound human and friendly, not salesy
- Reference their specific property interest
- End with a soft question to re-open conversation
- Do not use emojis
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()


# Store results
results = []

for index, row in df.iterrows():
    score, days = score_lead(row["last_contact"])
    message = generate_message(
        row["name"],
        row["property_interest"],
        row["location"],
        score,
        days
    )
    
    print(f"\n{row['name']} → {score} ({days} days ago)")
    print(f"Message: {message}")
    print("-" * 60)
    
    # Save this lead's result
    results.append({
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "location": row["location"],
        "property_interest": row["property_interest"],
        "last_contact": row["last_contact"],
        "days_since_contact": days,
        "score": score,
        "reactivation_message": message
    })

# Convert results to a dataframe and save
output_df = pd.DataFrame(results)
output_df.to_csv("reactivated_leads.csv", index=False)

print(f"\nDone. {len(results)} leads processed.")
print("Saved to reactivated_leads.csv")