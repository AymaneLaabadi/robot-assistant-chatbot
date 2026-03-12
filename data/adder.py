import json

# Variables you already have
title = ""
content = ""

# Path to your cleaned JSON file
file_path = "D:\\AI\\robot-assistant-chatbot\\data\\cleaned_emines_docs.json"

# 1️⃣ Load existing JSON data (if file exists)
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 2️⃣ Append the new element
data.append({
    "title": title,
    "content": content
})

# 3️⃣ Save back to JSON with pretty printing
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("New element added successfully!")