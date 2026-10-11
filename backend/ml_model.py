"""Illustrative educational NLP model; replace examples with representative labeled data for real use."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

DATA = [
("send deposit before viewing, wire transfer today",1),
("owner is overseas, pay booking fee now to reserve keys",1),
("urgent offer below market rent, payment by gift card only",1),
("no viewing possible, keys couriered after advance payment",1),
("transfer security deposit immediately or lose this deal",1),
("cash only, no lease, send money through wire transfer",1),
("I am abroad and cannot meet, pay refundable fee before visit",1),
("too good to be true price, act now and do not contact agent",1),
("pay token amount before we disclose exact address",1),
("deposit required before tour, payment through crypto",1),
("landlord refuses in-person viewing and requests bank transfer",1),
("contact only on messaging app, no viewing, advance payment",1),
("payment by gift cards, wire transfer, or cryptocurrency",1),
("application fee before viewing any property",1),
("landlord asks to bypass platform and pay directly now",1),
("no lease agreement, send deposit to hold property",1),
("apartment for rent, viewing can be arranged this weekend",0),
("monthly rent, standard lease agreement and refundable deposit",0),
("property manager can show apartment in person by appointment",0),
("two bedroom flat near transit, schedule a tour with agent",0),
("lease terms and maintenance details provided before signing",0),
("view the unit first and submit application through property office",0),
("rent includes water, tenant screening and written lease required",0),
("landlord available for in-person visit and lease questions",0),
("property has photos, address, and scheduled open house",0),
("standard security deposit due after lease is reviewed and signed",0),
("visit the property before making a decision",0),
("rental office provides a receipt for all payments",0),
("written contract describes rent, deposit, and move in date",0),
("no payment required to schedule an in-person tour",0),
]
MODEL = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), strip_accents="unicode")),
    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
])
MODEL.fit([x[0] for x in DATA], [x[1] for x in DATA])

PATTERNS = {
 "Upfront payment before viewing": r"\b(pay|payment|deposit|transfer|fee)\b.{0,55}\b(before|prior to|without)\b.{0,25}\b(view|visit|tour|see|meet)\b|\b(before|prior to)\b.{0,25}\b(view|visit|tour)\b.{0,35}\b(deposit|pay|fee)\b",
 "Urgency or pressure": r"\b(urgent|immediately|right now|act now|today only|limited time|hurry|last chance)\b",
 "Unusual payment method": r"\b(gift card|cryptocurrency|crypto|wire transfer|western union|moneygram)\b",
 "Owner claims to be overseas": r"\b(overseas|abroad|out of the country|travelling|traveling)\b",
 "Viewing restrictions or keys sent after payment": r"\b(no|cannot|can't|unable to)\b.{0,25}\b(viewing|view|meet|show)\b|\b(keys|key)\b.{0,35}\b(posted|courier|mail)\b",
 "Bypassing normal process": r"\b(bypass|skip)\b.{0,25}\b(platform|agent|process|contract)\b|\b(no lease|no contract)\b",
}

def analyze_listing(title, description, location="", monthly_rent=None, currency="INR", contact_method=""):
    text = " ".join([title or "", description or "", location or "", contact_method or ""])
    probability = float(MODEL.predict_proba([text])[0][1])
    combined = f"{title or ''} {description or ''} {contact_method or ''}"
    signals = [label for label, pattern in PATTERNS.items() if re.search(pattern, combined, re.I)]
    rent_note = None
    try:
        if monthly_rent not in (None, "") and float(monthly_rent) > 0 and float(monthly_rent) < 1000 and currency.upper() == "INR":
            signals.append("Very low stated monthly rent (verify local comparables)")
            rent_note = "Rent is unusually low for many Indian urban markets; compare similar local listings."
    except (ValueError, TypeError):
        pass
    score = int(round(min(100, max(0, probability * 72 + min(len(signals), 4) * 7))))
    level = "High" if score >= 65 else "Medium" if score >= 35 else "Low"
    prediction = {"High":"High risk indicators","Medium":"Some risk indicators","Low":"Few risk indicators"}[level]
    if not signals:
        signals = ["No configured warning phrase detected; verify the listing independently."]
    return {
      "risk_score": score, "risk_level": level, "prediction": prediction, "signals": signals,
      "rent_note": rent_note,
      "advice": [
        "View the property in person or arrange a trusted live tour before paying.",
        "Verify the owner or agent independently and read the lease before signing.",
        "Avoid gift cards, cryptocurrency, and irreversible transfers for rental deposits.",
        "Compare the rent and photos with independent listings in the same area."
      ],
      "model_note": "Educational prototype score; not a verified probability of fraud."
    }
