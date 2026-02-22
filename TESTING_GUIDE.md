# HateShield - Audience Analysis Testing Guide

## 🧪 Local Test Files

Three test HTML pages have been created for testing different sentiment distributions:

### 📗 test_positive.html
- **Content:** Restaurant wins award - all positive/celebratory comments
- **Expected Results:** ~90-100% positive, ~0-10% neutral/negative
- **Use Case:** Test system handles overwhelmingly positive sentiment

### 📕 test_negative.html  
- **Content:** Tax increase announcement - angry/frustrated comments
- **Expected Results:** ~80-90% negative, ~10-20% neutral
- **Use Case:** Test system detects negative sentiment and anger

### 📘 test_neutral.html
- **Content:** Traffic light installation - informational/neutral comments
- **Expected Results:** ~70-90% neutral, ~10-30% positive/negative
- **Use Case:** Test system handles factual, non-emotional content

### How to Use:
1. Open any test file (e.g., `test_positive.html`) in your browser
2. Copy the file path from the address bar (e.g., `file:///C:/Users/galla/Downloads/projects/HateShield/test_positive.html`)
3. Paste it into the Audience Analysis URL field on the dashboard
4. Click "Analyze Post Audience"
5. Verify the sentiment percentages match expected distributions

---

## 🌐 Real URLs That Should Work

### ✅ Sites That Work Well:
These types of sites typically allow automated access and have extractable comments:

1. **News Sites with Open Comment Sections:**
   - Reddit threads (when not requiring login)
   - Hacker News discussions: https://news.ycombinator.com/
   - Some news site articles (check they don't require login)

2. **Public Blogs:**
   - WordPress blogs with open comments
   - Medium articles (some have comments)
   - Personal tech/dev blogs

3. **Forums:**
   - StackOverflow questions
   - Public forum threads
   - Community discussion boards

### ❌ Sites That WON'T Work:

1. **Social Media (Require Login):**
   - ❌ LinkedIn posts
   - ❌ Facebook posts
   - ❌ Twitter/X (most content)
   - ❌ Instagram posts

2. **Heavy Anti-Bot Protection:**
   - Sites with Cloudflare challenges
   - Sites requiring CAPTCHA
   - Sites with JavaScript-only loading

---

## 🔍 Finding Good Test URLs

**Tips for finding working URLs:**

1. **Google Search:** `"blog post" + "comments" + topic`
2. **Look for:** Pages that load comments immediately (not via "Load More" button)
3. **Check:** Can you see comments without logging in?
4. **Test:** Copy URL to browser incognito/private mode first

**Example Search Queries:**
- "wordpress blog technology comments"
- "public forum discussion"
- "hacker news discussion"

---

## 🛠️ Troubleshooting

### Error: "Requires login/authentication"
→ Site needs you to be logged in. Try a different URL.

### Error: "Site is blocking automated access"
→ Anti-bot protection detected. Try a simpler blog or news site.

### Error: "No comments found on page"
→ Either:
  - Page has no comments
  - Comments load via JavaScript (not supported)
  - HTML structure doesn't match our patterns

### Solution: Use the test files!
The `test_positive.html`, `test_negative.html`, and `test_neutral.html` files are guaranteed to work and demonstrate the feature perfectly with different sentiment distributions.

---

## 📝 Example URLs to Try

**Local Test Files (Recommended):**
```
file:///C:/Users/galla/Downloads/projects/HateShield/test_positive.html
file:///C:/Users/galla/Downloads/projects/HateShield/test_negative.html
file:///C:/Users/galla/Downloads/projects/HateShield/test_neutral.html
```

**Hacker News Discussion:**
```
https://news.ycombinator.com/item?id=[any-post-id]
```

**Reddit (sometimes works without login):**
```
https://old.reddit.com/r/[subreddit]/comments/[post-id]/
```

**Note:** External URLs may change or require login over time. The local test files are the most reliable option for testing and demonstrating the Audience Analysis feature.

---

## 🎯 Quick Start

1. **Start Backend:**
   ```powershell
   cd backend
   python app.py
   ```

2. **Open Dashboard:**
   - Open `frontend/dashboard.html` in browser

3. **Test Locally:**
   - Open `test_positive.html` in another browser tab
   - Copy the full file:/// URL from address bar
   - Paste into Audience Analysis field
   - Click "Analyze Post Audience"
   - Should see ~90-100% positive sentiment!

4. **Try All Three:**
   - Test `test_negative.html` → expect ~80-90% negative
   - Test `test_neutral.html` → expect ~70-90% neutral
   - Verify system accurately detects different sentiment distributions

You should see accurate sentiment percentages and appropriate dominant emotions!
