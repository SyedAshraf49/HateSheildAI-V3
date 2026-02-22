from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time, traceback, re, html
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from ml.predictor import Predictor
from ml.image_predictor import ImagePredictor
from collections import Counter

app = Flask(__name__)
CORS(app)

# Correct names: model_path= , vectorizer_path=
predictor = Predictor(
    model_path="ml/hate_speech_model.pkl",
    vectorizer_path="ml/vectorizer.pkl"
)
image_predictor = ImagePredictor()

@app.route('/')
def home():
    return {'status': 'HateShield backend running'}

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json(force=True)
        text = data.get('text', '')
        start = time.time()
        result = predictor.analyze_text(text)
        result['processing_time_ms'] = int((time.time() - start) * 1000)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Image file is required.'}), 400

        file = request.files['image']
        if not file or file.filename == '':
            return jsonify({'error': 'Valid image file is required.'}), 400

        image_bytes = file.read()
        start = time.time()
        result = image_predictor.analyze_image(image_bytes, file.filename)
        result['processing_time_ms'] = int((time.time() - start) * 1000)

        if 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def _parse_comments_payload(data):
    comments = data.get('comments')
    if isinstance(comments, list):
        return [str(c).strip() for c in comments if str(c).strip()]

    raw_text = data.get('text', '')
    if isinstance(raw_text, str) and raw_text.strip():
        return [line.strip() for line in raw_text.splitlines() if line.strip()]

    return []

def _fetch_url_html(url: str, timeout_s: int = 10) -> str:
    parsed = urlparse(url)
    
    # Handle file:// URLs by reading from local filesystem
    if parsed.scheme == 'file':
        try:
            # Convert file:// URL to local path
            file_path = parsed.path
            # Handle Windows paths (remove leading / from /C:/...)
            if file_path.startswith('/') and len(file_path) > 2 and file_path[2] == ':':
                file_path = file_path[1:]
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f'⚠ Failed to read local file {url}: {e}')
            return ''
    
    # Handle http/https URLs
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return ''
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    with urlopen(req, timeout=timeout_s) as resp:
        charset = resp.headers.get_content_charset() or 'utf-8'
        raw = resp.read(2 * 1024 * 1024)
        decoded = raw.decode(charset, errors='replace')
    return decoded

def _detect_blocked_content(html: str, url: str) -> str:
    """Detect if page is blocked, requires login, or is inaccessible. Returns error message if blocked, empty string if OK."""
    if not html or len(html) < 200:
        return 'Page returned no content or very little content. The site may be blocking automated access.'
    
    html_lower = html.lower()
    
    # Check for login/auth requirements
    login_indicators = [
        ('sign in', 'log in'), ('sign in', 'login'), ('create account', 'register'),
        ('authentication required', 'auth required'), ('member login', 'user login'),
        ('please log in', 'you must log in'), ('access denied', 'permission denied')
    ]
    
    for indicators in login_indicators:
        if all(phrase in html_lower for phrase in indicators):
            domain = urlparse(url).netloc
            if 'linkedin' in domain:
                return '❌ LinkedIn requires login to view posts and comments. Try a public blog or news article instead.'
            elif 'facebook' in domain or 'fb.com' in domain:
                return '❌ Facebook requires login to view posts. Try a public news article or blog post instead.'
            elif 'twitter' in domain or 'x.com' in domain:
                return '❌ Twitter/X may require login for some content. Try a public blog or news article instead.'
            elif 'instagram' in domain:
                return '❌ Instagram requires login to view posts. Try a public news article or blog post instead.'
            else:
                return f'❌ This site requires login/authentication. Please use a publicly accessible page.'
    
    # Check for blocking/captcha
    block_indicators = [
        'access denied', 'blocked', 'captcha', 'robot', 'automated access',
        'unusual traffic', 'verify you are human', 'security check',
        'forbidden', '403 forbidden', 'rate limit'
    ]
    
    block_count = sum(1 for phrase in block_indicators if phrase in html_lower)
    if block_count >= 2:
        return '❌ Site is blocking automated access (anti-bot protection detected). Try a different URL.'
    
    # Check for error pages
    if '404 not found' in html_lower or 'page not found' in html_lower:
        return '❌ Page not found (404). Please check the URL is correct.'
    
    if '500 internal server' in html_lower or 'server error' in html_lower:
        return '❌ Server error at the target site. Try again later.'
    
    return ''

def _clean_html_fragment(fragment: str) -> str:
    text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', fragment or '')
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _extract_comments_from_html(raw_html: str, max_comments: int = 500):
    if not raw_html:
        return []

    comments = []

    # PRIORITY 1: Extract from specific comment content classes (more targeted)
    specific_blocks = re.findall(
        r'(?is)<(?:div|p|span)[^>]*(?:id|class)=["\"][^"\"]*'
        r'(?:comment-text|comment-body|comment-content|reply-text|review-text|message-text)[^"\"]*["\"][^>]*>(.*?)</(?:div|p|span)>',
        raw_html,
    )

    for block in specific_blocks:
        cleaned = _clean_html_fragment(block)
        if 10 <= len(cleaned) <= 800:
            comments.append(cleaned)

    # PRIORITY 2: If not enough, try broader comment/reply/review patterns
    if len(comments) < 5:
        tagged_blocks = re.findall(
            r'(?is)<(?:div|p|li|span|article)[^>]*(?:id|class)=["\"][^"\"]*'
            r'(?:comment|reply|review|message|thread|post|feedback)[^"\"]*["\"][^>]*>(.*?)</(?:div|p|li|span|article)>',
            raw_html,
        )

        for block in tagged_blocks:
            cleaned = _clean_html_fragment(block)
            if 10 <= len(cleaned) <= 800:
                comments.append(cleaned)

    # PRIORITY 3: Fallback - extract from common paragraph and div tags
    if len(comments) < 3:
        text_candidates = re.findall(r'(?is)<(?:p|div|li)[^>]*>(.*?)</(?:p|div|li)>', raw_html)
        for candidate in text_candidates:
            cleaned = _clean_html_fragment(candidate)
            if 10 <= len(cleaned) <= 350:
                comments.append(cleaned)

    # Deduplicate - remove exact duplicates AND substring duplicates
    unique_comments = []
    seen_normalized = set()
    
    for c in comments:
        normalized = re.sub(r'\W+', '', c.lower())
        if len(normalized) < 5:
            continue
            
        # Check if this is an exact duplicate
        if normalized in seen_normalized:
            continue
            
        # Check if this is a substring of an existing comment (or vice versa)
        is_duplicate = False
        comments_to_remove = []
        
        for idx, existing in enumerate(unique_comments):
            existing_normalized = re.sub(r'\W+', '', existing.lower())
            
            # If new comment is substring of existing, skip it
            if normalized in existing_normalized:
                is_duplicate = True
                break
            
            # If existing is substring of new comment, mark existing for removal
            if existing_normalized in normalized:
                comments_to_remove.append(idx)
        
        if is_duplicate:
            continue
            
        # Remove substrings
        for idx in sorted(comments_to_remove, reverse=True):
            del unique_comments[idx]
            
        seen_normalized.add(normalized)
        unique_comments.append(c)
        
        if len(unique_comments) >= max_comments:
            break

    print(f'✓ Extracted {len(unique_comments)} unique comments from HTML')
    return unique_comments

def _sentiment_bucket(classification: str, emotions: dict) -> str:
    classification = (classification or '').lower()
    joy = int((emotions or {}).get('joy', 0))
    anger = int((emotions or {}).get('anger', 0))
    fear = int((emotions or {}).get('fear', 0))
    sadness = int((emotions or {}).get('sadness', 0))
    disgust = int((emotions or {}).get('disgust', 0))

    # Only truly hateful content is immediately negative
    if classification in ('hate_speech', 'toxic'):
        return 'negative'
    
    # For 'offensive', check if emotions support negativity
    if classification == 'offensive':
        if max(anger, fear, sadness, disgust) >= 25:
            return 'negative'
        # Otherwise fall through to emotion-based classification

    # POSITIVE: Joy is dominant
    if joy >= max(anger, fear, sadness, disgust) and joy >= 20:
        return 'positive'
    
    # NEGATIVE: Strong negative emotions
    neg_emotions_sum = anger + fear + sadness + disgust
    if neg_emotions_sum >= 50 or max(anger, fear, sadness, disgust) >= 35:
        return 'negative'
    
    # DEFAULT: Safe comments with low emotions are positive/neutral
    if classification == 'safe':
        # Slight positive bias for safe content
        if joy >= 10 or neg_emotions_sum < 20:
            return 'positive'

    return 'neutral'

def _dominant_reaction_label(text: str, emotions: dict, classification: str) -> str:
    t = (text or '').lower()
    classification = (classification or '').lower()

    sarcasm_markers = ['/s', 'yeah right', 'sure buddy', 'as if', 'totally', 'wow amazing', 'nice job']
    support_markers = ['support', 'we stand with', 'stay strong', 'proud of you', 'i appreciate', 'well done']

    if any(marker in t for marker in sarcasm_markers):
        return 'sarcasm'
    if any(marker in t for marker in support_markers):
        return 'support'

    if classification in ('hate_speech', 'toxic', 'offensive'):
        return 'anger'

    emotion_scores = {
        'anger': int((emotions or {}).get('anger', 0)),
        'support': int((emotions or {}).get('joy', 0)),
        'fear': int((emotions or {}).get('fear', 0)),
        'sadness': int((emotions or {}).get('sadness', 0)),
        'disgust': int((emotions or {}).get('disgust', 0)),
        'neutral': 20,
    }
    return max(emotion_scores, key=emotion_scores.get)

@app.route('/analyze_audience', methods=['POST'])
def analyze_audience():
    try:
        data = request.get_json(force=True) or {}

        source_url = (data.get('post_url') or data.get('url') or '').strip()
        comments = []
        extraction_mode = 'manual'
        extraction_error = None

        if source_url:
            try:
                # Fetch HTML from URL (handles both http/https and file://)
                raw_html = _fetch_url_html(source_url)
                    
                if not raw_html:
                    extraction_error = 'Unable to fetch content from URL'
                else:
                    # Check if page is blocked or requires login
                    block_error = _detect_blocked_content(raw_html, source_url)
                    if block_error:
                        extraction_error = block_error
                    else:
                        comments = _extract_comments_from_html(raw_html)
                        extraction_mode = 'url'
                        if not comments:
                            # Provide helpful suggestions based on domain
                            domain = urlparse(source_url).netloc
                            suggestion = ''
                            if any(social in domain for social in ['linkedin', 'facebook', 'twitter', 'instagram', 'x.com']):
                                suggestion = ' Social media sites often require login. Try a public blog or news article instead.'
                            extraction_error = f'No comments found on page. Extracted {len(raw_html)} bytes of HTML but found no comment-like text blocks.{suggestion}'
            except Exception as fetch_error:
                extraction_error = f'Failed to fetch URL: {str(fetch_error)}'
                print(f'⚠ Audience URL fetch error: {fetch_error}')
                traceback.print_exc()

        if not comments:
            comments = _parse_comments_payload(data)

        if not comments:
            error_msg = extraction_error or 'At least one comment is required.'
            return jsonify({'error': error_msg}), 400

        if len(comments) > 500:
            comments = comments[:500]

        start = time.time()

        sentiment_counts = Counter({'positive': 0, 'negative': 0, 'neutral': 0})
        reaction_counts = Counter()
        analyzed = 0

        for comment in comments:
            result = predictor.analyze_text(comment)
            classification = result.get('classification', 'safe')
            if classification == 'invalid':
                continue

            emotions = result.get('emotions', {})
            sentiment = _sentiment_bucket(classification, emotions)
            reaction = _dominant_reaction_label(comment, emotions, classification)

            sentiment_counts[sentiment] += 1
            reaction_counts[reaction] += 1
            analyzed += 1

        if analyzed == 0:
            return jsonify({'error': 'No valid comments to analyze.'}), 400

        positive_percent = round((sentiment_counts['positive'] / analyzed) * 100, 1)
        negative_percent = round((sentiment_counts['negative'] / analyzed) * 100, 1)
        neutral_percent = round((sentiment_counts['neutral'] / analyzed) * 100, 1)

        dominant_emotion = reaction_counts.most_common(1)[0][0] if reaction_counts else 'neutral'

        return jsonify({
            'total_comments': len(comments),
            'analyzed_comments': analyzed,
            'positive_percent': positive_percent,
            'negative_percent': negative_percent,
            'neutral_percent': neutral_percent,
            'dominant_emotion': dominant_emotion,
            'trend_breakdown': dict(reaction_counts),
            'source_url': source_url,
            'extraction_mode': extraction_mode,
            'processing_time_ms': int((time.time() - start) * 1000)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_post', methods=['POST'])
def analyze_post():
    """Comprehensive social media post analysis for pre-publication review"""
    try:
        data = request.get_json(force=True) or {}
        
        caption = (data.get('caption') or '').strip()
        hashtags = (data.get('hashtags') or '').strip()
        description = (data.get('description') or '').strip()
        target_audience = (data.get('target_audience') or '').strip()
        
        if not any([caption, hashtags, description]):
            return jsonify({'error': 'At least one content field (caption, hashtags, or description) is required.'}), 400
        
        start = time.time()
        
        # 1. CONTENT QUALITY ANALYSIS
        quality_issues = []
        quality_score = 100
        
        # Analyze combined text length
        combined_text = f"{caption} {description}".strip()
        combined_text_lower = combined_text.lower()
        if len(combined_text) < 20:
            quality_issues.append("Content is too short - aim for at least 20 characters to provide value")
            quality_score -= 20
        elif len(combined_text) < 50:
            quality_issues.append("Content could be more detailed - consider expanding your message")
            quality_score -= 10
        
        # Check for call-to-action
        cta_keywords = ['click', 'link in bio', 'swipe up', 'comment below', 'tag a friend', 
                       'share', 'follow', 'subscribe', 'check out', 'learn more', 'visit']
        has_cta = any(keyword in combined_text.lower() for keyword in cta_keywords)
        if not has_cta:
            quality_issues.append("Consider adding a call-to-action (CTA) to drive engagement")
            quality_score -= 15
        
        # 2. TOXICITY RISK ANALYSIS
        toxicity_results = []
        max_toxicity_confidence = 0
        toxic_parts = []

        # Rule-based toxicity checks for exclusionary/hostile phrasing
        high_risk_patterns = [
            r'\bpeople from (that|this) group\b',
            r'\bthey should stay away\b',
            r'\bdo not belong\b',
            r'\bshould not be here\b',
            r'\bget out\b',
            r'\bkeep them away\b',
        ]

        medium_risk_patterns = [
            r'\bruin everything\b',
            r'\bnever contribute\b',
            r'\bonly create problems\b',
            r'\buseless\b',
            r'\bfed up\b',
            r'\btired of\b',
            r'\bcan\'t stand them\b',
        ]

        high_hits = sum(1 for pattern in high_risk_patterns if re.search(pattern, combined_text_lower))
        medium_hits = sum(1 for pattern in medium_risk_patterns if re.search(pattern, combined_text_lower))

        if high_hits > 0:
            heuristic_conf = min(95, 80 + (high_hits * 5))
            toxicity_results.append({
                'part': 'content',
                'classification': 'hate_speech',
                'confidence': heuristic_conf,
                'source': 'rule_based'
            })
            max_toxicity_confidence = max(max_toxicity_confidence, heuristic_conf)
            toxic_parts.append('content')
        elif medium_hits >= 2:
            heuristic_conf = min(75, 50 + (medium_hits * 8))
            toxicity_results.append({
                'part': 'content',
                'classification': 'offensive',
                'confidence': heuristic_conf,
                'source': 'rule_based'
            })
            max_toxicity_confidence = max(max_toxicity_confidence, heuristic_conf)
            toxic_parts.append('content')
        
        # Analyze caption
        if caption:
            caption_result = predictor.analyze_text(caption)
            if caption_result.get('classification') not in ('safe', 'invalid'):
                toxicity_results.append({
                    'part': 'caption',
                    'classification': caption_result.get('classification'),
                    'confidence': caption_result.get('confidence', 0)
                })
                max_toxicity_confidence = max(max_toxicity_confidence, caption_result.get('confidence', 0))
                toxic_parts.append('caption')
        
        # Analyze description
        if description:
            desc_result = predictor.analyze_text(description)
            if desc_result.get('classification') not in ('safe', 'invalid'):
                toxicity_results.append({
                    'part': 'description',
                    'classification': desc_result.get('classification'),
                    'confidence': desc_result.get('confidence', 0)
                })
                max_toxicity_confidence = max(max_toxicity_confidence, desc_result.get('confidence', 0))
                toxic_parts.append('description')
        
        # Analyze hashtags for problematic content
        if hashtags:
            # Remove # symbols and split
            hashtag_list = re.findall(r'#?(\w+)', hashtags)
            problematic_tags = []
            
            for tag in hashtag_list:
                tag_result = predictor.analyze_text(tag)
                if tag_result.get('classification') not in ('safe', 'invalid'):
                    problematic_tags.append(f"#{tag}")
            
            if problematic_tags:
                toxicity_results.append({
                    'part': 'hashtags',
                    'problematic_tags': problematic_tags,
                    'classification': 'offensive'
                })
                toxic_parts.append('hashtags')
        
        # Determine risk level
        if max_toxicity_confidence >= 70 or len(toxic_parts) >= 2:
            risk_level = 'HIGH'
            risk_color = '#ef4444'
        elif max_toxicity_confidence >= 50 or len(toxic_parts) >= 1:
            risk_level = 'MEDIUM'
            risk_color = '#f59e0b'
        else:
            risk_level = 'LOW'
            risk_color = '#10b981'
        
        # 3. ENGAGEMENT PREDICTION
        engagement_score = 50  # Base score
        engagement_factors = []
        
        # Hashtag analysis
        if hashtags:
            hashtag_count = len(re.findall(r'#\w+', hashtags))
            if 3 <= hashtag_count <= 10:
                engagement_score += 15
                engagement_factors.append(f"Good hashtag count ({hashtag_count})")
            elif hashtag_count > 15:
                engagement_score -= 10
                engagement_factors.append(f"Too many hashtags ({hashtag_count}) - can appear spammy")
            elif hashtag_count > 0:
                engagement_score += 5
                engagement_factors.append(f"Has hashtags ({hashtag_count})")
        else:
            engagement_factors.append("No hashtags - adding relevant tags can increase reach")
        
        # Content length and structure
        if 50 <= len(combined_text) <= 300:
            engagement_score += 10
            engagement_factors.append("Optimal content length")
        elif len(combined_text) > 300:
            engagement_score += 5
            engagement_factors.append("Detailed content (may require 'read more' click)")
        
        # CTA presence
        if has_cta:
            engagement_score += 15
            engagement_factors.append("Includes call-to-action")
        
        # Emojis (moderate use increases engagement)
        emoji_count = sum(1 for char in combined_text if ord(char) > 0x1F300)
        if 1 <= emoji_count <= 5:
            engagement_score += 10
            engagement_factors.append("Good emoji usage")
        elif emoji_count > 8:
            engagement_score -= 5
            engagement_factors.append("Excessive emojis may reduce professionalism")
        
        # Question marks (encourage interaction)
        if '?' in combined_text:
            engagement_score += 8
            engagement_factors.append("Asks questions (encourages interaction)")
        
        # Target audience consideration
        if target_audience:
            engagement_score += 10
            engagement_factors.append(f"Targeted for: {target_audience}")
        
        # Toxicity penalty
        if risk_level == 'HIGH':
            engagement_score -= 40
            engagement_factors.append("High toxicity risk significantly reduces reach")
        elif risk_level == 'MEDIUM':
            engagement_score -= 20
            engagement_factors.append("Toxicity risk may limit audience reach")
        
        engagement_score = max(0, min(100, engagement_score))
        
        # 4. GENERATE SUGGESTIONS
        suggestions = []
        
        if risk_level in ('HIGH', 'MEDIUM'):
            suggestions.append({
                'priority': 'critical',
                'category': 'toxicity',
                'message': f"Review and revise {', '.join(toxic_parts)} to remove offensive/toxic content before posting"
            })
        
        if quality_score < 70:
            for issue in quality_issues:
                suggestions.append({
                    'priority': 'medium',
                    'category': 'quality',
                    'message': issue
                })
        
        if not hashtags:
            suggestions.append({
                'priority': 'medium',
                'category': 'engagement',
                'message': "Add 5-10 relevant hashtags to increase discoverability"
            })
        
        if not target_audience:
            suggestions.append({
                'priority': 'low',
                'category': 'targeting',
                'message': "Define your target audience for better content optimization"
            })
        
        if engagement_score < 60:
            suggestions.append({
                'priority': 'medium',
                'category': 'engagement',
                'message': "Consider adding more engaging elements (questions, CTAs, emojis) to boost interaction"
            })
        
        # 5. CONTENT QUALITY VERDICT
        is_good_content = (
            risk_level == 'LOW' and 
            quality_score >= 70 and 
            engagement_score >= 60
        )
        
        # 6. ENGAGEMENT VS TOXICITY COMPARISON
        comparison = {
            'engagement_score': engagement_score,
            'toxicity_risk': max_toxicity_confidence,
            'balance': 'positive' if (engagement_score > max_toxicity_confidence + 20) else 
                      ('negative' if max_toxicity_confidence > engagement_score else 'neutral'),
            'recommendation': 'safe_to_post' if is_good_content else 'needs_revision'
        }
        
        processing_time_ms = int((time.time() - start) * 1000)
        
        return jsonify({
            'is_good_content': is_good_content,
            'quality_score': quality_score,
            'engagement_score': engagement_score,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'toxicity_results': toxicity_results,
            'suggestions': suggestions,
            'comparison': comparison,
            'engagement_factors': engagement_factors,
            'target_audience': target_audience or 'General audience',
            'processing_time_ms': processing_time_ms,
            'report': {
                'caption': caption,
                'hashtags': hashtags,
                'description': description,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'verdict': 'APPROVED' if is_good_content else 'NEEDS REVISION'
            }
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)