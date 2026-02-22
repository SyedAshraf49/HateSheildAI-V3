import os, joblib, re
from typing import Dict

class Predictor:
    """
    Enhanced predictor with improved accuracy and numeric input validation.
    """

    def __init__(self, model_path='ml/hate_speech_model.pkl', vectorizer_path='ml/vectorizer.pkl'):
        self.model = None
        self.vectorizer = None
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                print('Loaded ML model and vectorizer.')
            else:
                print('ML model or vectorizer not found; using rule-based fallback.')
                print(f'  Looking for: {self.model_path} and {self.vectorizer_path}')
        except Exception as e:
            print('Failed loading model/vectorizer:', e)
            self.model = None
            self.vectorizer = None

    def analyze_text(self, text: str) -> Dict:
        text = text or ''
        
        # Check if input is only numbers
        if self._is_only_numbers(text.strip()):
            emotions = {'anger': 0, 'fear': 0, 'sadness': 0, 'disgust': 0, 'joy': 0}
            return {
                'original_text': text,
                'classification': 'invalid',
                'confidence': 0,
                'emotions': emotions,
                'dominant_emotion': self._get_dominant_emotion(emotions),
                'rewritten_text': self._generate_safe_rewrite(text),
                'warning': 'Input contains only numbers. Please provide meaningful text for analysis.'
            }
        
        # Check for very short input
        if len(text.strip()) < 3:
            emotions = {'anger': 0, 'fear': 0, 'sadness': 0, 'disgust': 0, 'joy': 0}
            return {
                'original_text': text,
                'classification': 'invalid',
                'confidence': 0,
                'emotions': emotions,
                'dominant_emotion': self._get_dominant_emotion(emotions),
                'rewritten_text': self._generate_safe_rewrite(text),
                'warning': 'Input is too short. Please provide at least 3 characters.'
            }
        
        # if ML model available, use it
        if self.model and self.vectorizer:
            try:
                cleaned = self._clean_text(text)
                X = self.vectorizer.transform([cleaned])
                pred = self.model.predict(X)[0]
                try:
                    prob = max(self.model.predict_proba(X)[0]) * 100
                except Exception:
                    prob = 80.0
                
                # Enhanced classification mapping
                classification = self._get_enhanced_classification(text, pred, prob)
                confidence = int(min(100, max(10, round(prob))))
                emotions = self._estimate_emotions(text, classification)
                dominant_emotion = self._get_dominant_emotion(emotions)
                rewritten = self._generate_rewrite(text, classification, dominant_emotion)
                
                return {
                    'original_text': text, 
                    'classification': classification, 
                    'confidence': confidence, 
                    'emotions': emotions, 
                    'dominant_emotion': dominant_emotion,
                    'rewritten_text': rewritten
                }
            except Exception as e:
                print('Model prediction failed, falling back to rules:', e)
        
        # Enhanced fallback
        return self._rule_based(text)

    def _is_only_numbers(self, text):
        """Check if input contains only numbers, spaces, and basic punctuation"""
        cleaned = re.sub(r'[0-9\s\.\,\-\+\=\(\)\[\]\{\}\/\\\:\;]', '', text)
        return len(cleaned) == 0 and len(text) > 0

    def _get_enhanced_classification(self, text, pred, prob):
        """Enhanced classification with context awareness"""
        t = text.lower()

        offensive_keywords = [
            'stupid', 'idiot', 'moron', 'dumb', 'trash', 'garbage',
            'worthless', 'pathetic', 'loser', 'useless', 'shut up'
        ]
        
        # Severe threat keywords
        severe_threats = [
            'kill yourself', 'kys', 'i will kill', "i'll kill", 'shoot you',
            'burn in hell', 'hope you die', 'you should die', 'drop dead', 'go die'
        ]
        hate_keywords = [
            'go back to', 'your kind', 'exterminate', 'subhuman', 'genocide',
            'ethnic cleansing', 'kill all', 'do not belong here'
        ]
        
        # Check for severe content first
        if self._contains_phrase(t, severe_threats):
            return 'toxic'
        if self._contains_phrase(t, hate_keywords):
            return 'hate_speech'
        if self._contains_phrase(t, offensive_keywords):
            return 'offensive'
        
        # Use model prediction with STRICTER confidence thresholds to reduce false positives
        if pred == 0 or prob < 65:
            # Default to safe unless we have strong evidence
            return 'safe'
        elif pred == 1 and prob > 85:
            # Only classify as toxic with very high confidence
            toxic_indicators = ['stupid', 'idiot', 'moron', 'dumb', 'trash', 'garbage', 
                              'worthless', 'pathetic', 'loser']
            if self._contains_phrase(t, toxic_indicators):
                return 'offensive'
            return 'toxic'
        elif pred == 1 and prob > 70:
            # Medium-high confidence -> offensive
            return 'offensive'
        else:
            return 'safe'

    def _rule_based(self, text):
        """Enhanced rule-based classification with better accuracy"""
        t = (text or "").lower()
        
        # More comprehensive keyword lists
        hate_keywords = [
            'go back to', 'your kind', 'subhuman', 'genocide', 'ethnic cleansing',
            'kill all', 'kill them', 'do not belong here', 'do not belong'
        ]
        
        abusive = ['stupid', 'idiot', 'dumb', 'suck', 'trash', 'moron', 'ugly', 
                  'worthless', 'garbage', 'shut up', 'loser', 'pathetic', 'fool',
                  'retard', 'cretin', 'imbecile']
        
        threat = ['kill yourself', 'kys', 'drop dead', 'i will kill', "i'll kill", 
             'go die', 'i hope you die', 'you should die', 'i will hurt you', 'burn in hell', 
                 'go to hell', 'shoot you', 'stab you', 'murder you']
        
        profanity = ['fuck', 'shit', 'damn', 'hell', 'ass', 'bitch', 'bastard', 'crap']
        
        positive = ['love', 'thank', 'great', 'amazing', 'wonderful', 'excellent', 
                   'appreciate', 'fantastic', 'brilliant', 'awesome']
        
        score = 0
        
        # Check for positive content first
        positive_count = sum(1 for k in positive if self._contains_phrase(t, [k]))
        if positive_count >= 2:
            emotions = self._estimate_emotions(text, 'safe')
            dominant_emotion = self._get_dominant_emotion(emotions)
            return {
                'original_text': text,
                'classification': 'safe',
                'confidence': 90,
                'emotions': emotions,
                'dominant_emotion': dominant_emotion,
                'rewritten_text': self._generate_safe_rewrite(text, dominant_emotion)
            }
        
        # Score negative content
        for k in hate_keywords:
            if self._contains_phrase(t, [k]):
                score += 60
        for k in abusive:
            if self._contains_phrase(t, [k]):
                score += 25
        for k in threat:
            if self._contains_phrase(t, [k]):
                score += 80
        for k in profanity:
            if self._contains_phrase(t, [k]):
                score += 15
        
        # Check for ALL CAPS (shouting)
        if text.isupper() and len(text) > 5:
            score += 20
        
        # Multiple exclamation marks
        exclaim_count = text.count('!')
        if exclaim_count >= 3:
            score += 15
        
        # Determine classification
        if self._contains_phrase(t, threat):
            classification = 'toxic'
        elif self._contains_phrase(t, hate_keywords):
            classification = 'hate_speech'
        elif score >= 50:
            classification = 'offensive'
        elif score >= 25:
            classification = 'offensive'
        else:
            classification = 'safe'
        
        confidence = min(100, max(30, score + 30))
        emotions = self._estimate_emotions(text, classification)
        dominant_emotion = self._get_dominant_emotion(emotions)
        rewritten = self._generate_rewrite(text, classification, dominant_emotion)
        
        return {
            'original_text': text, 
            'classification': classification, 
            'confidence': confidence, 
            'emotions': emotions, 
            'dominant_emotion': dominant_emotion,
            'rewritten_text': rewritten
        }

    def _get_dominant_emotion(self, emotions):
        if not emotions:
            return 'neutral'
        dominant_key = max(emotions, key=emotions.get)
        if (emotions.get(dominant_key) or 0) <= 0:
            return 'neutral'
        return dominant_key

    def _contains_phrase(self, text, phrases):
        text = text or ''
        for phrase in phrases:
            normalized = re.escape(phrase).replace(r'\ ', r'\s+')
            pattern = rf'(?<!\w){normalized}(?!\w)'
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False

    def _count_phrase_hits(self, text, phrase_weights):
        text = text or ''
        score = 0
        for phrase, weight in phrase_weights.items():
            normalized = re.escape(phrase).replace(r'\ ', r'\s+')
            pattern = rf'(?<!\w){normalized}(?!\w)'
            if re.search(pattern, text, flags=re.IGNORECASE):
                score += weight
        return score

    def _clean_text(self, text):
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[^a-zA-Z ]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    def _estimate_emotions(self, text, classification):
        """Significantly improved emotion estimation"""
        t = (text or '').lower()
        
        # Initialize
        anger = joy = sadness = fear = disgust = 0
        
        # ANGER - Comprehensive detection
        anger_strong = {
            'hate': 35, 'furious': 35, 'enraged': 35, 'livid': 35, 'seething': 35,
            'outraged': 35, 'infuriated': 35, 'rage': 35, 'angry': 35, 'pissed': 35
        }
        anger_medium = {
            'mad': 20, 'annoyed': 20, 'irritated': 20, 'frustrated': 20,
            'upset': 20, 'bothered': 20
        }
        aggressive = {
            'kill': 30, 'destroy': 30, 'attack': 30, 'fight': 30,
            'punch': 30, 'hit': 30, 'smash': 30, 'break': 30
        }
        insults = {
            'idiot': 18, 'stupid': 18, 'moron': 18, 'fool': 18, 'dumb': 18,
            'pathetic': 18, 'worthless': 18, 'loser': 18, 'trash': 18, 'garbage': 18
        }

        anger += self._count_phrase_hits(t, anger_strong)
        anger += self._count_phrase_hits(t, anger_medium)
        anger += self._count_phrase_hits(t, aggressive)
        anger += self._count_phrase_hits(t, insults)
        
        # Check for caps and exclamation
        if text:
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            if caps_ratio > 0.5: anger += 30
            elif caps_ratio > 0.3: anger += 20
        
        if text.count('!') >= 3: anger += 25
        elif text.count('!') >= 2: anger += 15
        
        # JOY - Enhanced detection
        joy_strong = {
            'love': 30, 'amazing': 30, 'fantastic': 30, 'wonderful': 30, 'excellent': 30,
            'perfect': 30, 'brilliant': 30, 'ecstatic': 30, 'thrilled': 30, 'awesome': 30
        }
        joy_medium = {
            'happy': 18, 'great': 18, 'good': 18, 'nice': 18, 'pleased': 18,
            'glad': 18, 'excited': 18, 'delighted': 18, 'enjoy': 18
        }
        gratitude = {
            'thank': 25, 'thanks': 25, 'appreciate': 25, 'grateful': 25,
            'blessing': 25, 'blessed': 25
        }

        joy += self._count_phrase_hits(t, joy_strong)
        joy += self._count_phrase_hits(t, joy_medium)
        joy += self._count_phrase_hits(t, gratitude)
        
        # SADNESS - Better detection
        sadness_strong = {
            'depressed': 35, 'miserable': 35, 'devastated': 35, 'heartbroken': 35,
            'grief': 35, 'hopeless': 35, 'despair': 35
        }
        sadness_medium = {
            'sad': 22, 'unhappy': 22, 'upset': 22, 'disappointed': 22,
            'hurt': 22, 'pain': 22, 'suffer': 22, 'crying': 22
        }
        loss = {
            'loss': 25, 'lost': 25, 'lonely': 25, 'alone': 25, 'empty': 25,
            'miss': 25
        }

        sadness += self._count_phrase_hits(t, sadness_strong)
        sadness += self._count_phrase_hits(t, sadness_medium)
        sadness += self._count_phrase_hits(t, loss)
        
        # FEAR - Enhanced detection
        fear_strong = {
            'terrified': 35, 'horrified': 35, 'panic': 35, 'petrified': 35,
            'nightmare': 35, 'terror': 35
        }
        fear_medium = {
            'scared': 22, 'afraid': 22, 'frightened': 22, 'anxious': 22,
            'worried': 22, 'nervous': 22
        }
        fear_threat = {
            'threat': 28, 'danger': 28, 'risk': 28, 'warning': 28,
            'alert': 28, 'emergency': 28
        }

        fear += self._count_phrase_hits(t, fear_strong)
        fear += self._count_phrase_hits(t, fear_medium)
        fear += self._count_phrase_hits(t, fear_threat)
        
        # DISGUST - Better detection
        disgust_strong = {
            'disgusting': 35, 'disgusted': 35, 'revolting': 35, 'repulsive': 35,
            'vomit': 35, 'puke': 35, 'vile': 35, 'repugnant': 35
        }
        disgust_medium = {
            'gross': 22, 'nasty': 22, 'sick': 22, 'horrible': 22,
            'awful': 22, 'terrible': 22
        }

        disgust += self._count_phrase_hits(t, disgust_strong)
        disgust += self._count_phrase_hits(t, disgust_medium)
        
        # Classification-based adjustments
        if classification == 'toxic' or classification == 'hate_speech':
            anger = min(100, anger + 40)
            disgust = min(100, disgust + 35)
            joy = max(0, joy - 50)
            fear = min(100, fear + 20)
        elif classification == 'offensive':
            anger = min(100, anger + 30)
            disgust = min(100, disgust + 25)
            joy = max(0, joy - 30)
        elif classification == 'safe':
            if joy > 20:
                joy = min(100, joy + 20)
                anger = max(0, anger - 15)
                disgust = max(0, disgust - 15)
        
        # Normalize
        anger = min(100, max(0, anger))
        joy = min(100, max(0, joy))
        sadness = min(100, max(0, sadness))
        fear = min(100, max(0, fear))
        disgust = min(100, max(0, disgust))
        
        return {
            'anger': anger, 
            'fear': fear, 
            'sadness': sadness, 
            'disgust': disgust, 
            'joy': joy
        }

    def _generate_rewrite(self, text, classification, dominant_emotion='neutral'):
        if classification == 'safe':
            return self._generate_safe_rewrite(text, dominant_emotion)
        
        r = text or ''
        
        # More comprehensive replacements
        offensive_replacements = {
            r'\b(stupid|idiot|dumb|moron|fool|retard)\b': 'mistaken',
            r'\b(trash|garbage|worthless|useless)\b': 'inadequate',
            r'\b(suck|awful|terrible)\b': 'unsatisfactory',
            r'\b(shut up|be quiet)\b': 'please stop',
            r'\b(ugly|hideous)\b': 'unattractive',
            r'\b(loser|failure)\b': 'person',
            r'\b(pathetic)\b': 'unfortunate',
            r'\b(fuck|fucking|fucked)\b': 'very',
            r'\b(shit|shitty)\b': 'bad',
            r'\b(damn|damned)\b': 'very',
            r'\b(hell)\b': 'heck',
            r'\b(ass|asshole)\b': 'person',
            r'\b(bitch|bitchy)\b': 'person'
        }
        
        for pattern, replacement in offensive_replacements.items():
            r = re.sub(pattern, replacement, r, flags=re.IGNORECASE)
        
        # Replace hate speech
        r = re.sub(r'\b(hate|hated|hating)\b', 'dislike', r, flags=re.IGNORECASE)
        r = re.sub(r'\b(racist|racism|nazi|bigot)\b', 
                   'discriminatory language', r, flags=re.IGNORECASE)
        r = re.sub(r'\b(your kind|subhuman|genocide|ethnic cleansing)\b',
               '[hateful language removed]', r, flags=re.IGNORECASE)
        r = re.sub(r'\b(do not belong here|do not belong|go back to|kill all|kill them)\b',
               '[hateful language removed]', r, flags=re.IGNORECASE)
        
        # Replace threats
        threat_patterns = [
            r'\b(kill yourself|kys|drop dead|go die)\b',
            r'\b(i will kill|i\'ll kill|gonna kill)\b',
            r'\b(i hope you die|you should die)\b',
            r'\b(burn in hell|go to hell)\b'
        ]
        for pattern in threat_patterns:
            r = re.sub(pattern, '[threatening language removed]', r, flags=re.IGNORECASE)

        r = re.sub(r'\s+', ' ', r).strip()
        if not r:
            r = '[content removed]'

        core_text = r.strip().rstrip(' .!?')
        if not core_text:
            core_text = '[content removed]'
        
        # Add respectful prefix
        if classification in ['toxic', 'hate_speech']:
            if '[threatening language removed]' in r or '[hateful language removed]' in r:
                r = 'I strongly disagree, but I want to express it respectfully.'
            else:
                r = 'I disagree with this and want to discuss it respectfully: ' + core_text
        else:
            r = 'I would like to express this more constructively: ' + core_text
        
        if not r.endswith('.'):
            r += '.'
        
        return r

    def _generate_safe_rewrite(self, text, dominant_emotion='neutral'):
        source = (text or '').strip()
        if not source:
            return ''

        source_was_upper = source.isupper()
        polished = re.sub(r'\s+', ' ', source)

        # Normalize common shorthand/abbreviations
        shorthand_map = {
            r'\bpls\b': 'please',
            r'\bplz\b': 'please',
            r'\bthx\b': 'thank you',
            r'\bty\b': 'thank you',
            r'\bu\b': 'you',
            r'\bur\b': 'your',
            r'\bimo\b': 'in my opinion',
            r'\bidk\b': 'I am not sure',
            r'\basap\b': 'as soon as possible',
            r'\bim\b': "I'm",
            r'\bi\'m\b': "I'm",
        }
        for pattern, replacement in shorthand_map.items():
            polished = re.sub(pattern, replacement, polished, flags=re.IGNORECASE)

        # Remove excessive repeated punctuation
        polished = re.sub(r'([!?.,])\1{1,}', r'\1', polished)

        # Soften direct conflict language while preserving intent
        soften_rules = [
            (r'\byou are wrong\b', 'I see this differently'),
            (r'\bthis is wrong\b', 'this may need revision'),
            (r'\bi disagree\b', 'I respectfully disagree'),
            (r'\bthat makes no sense\b', 'that is unclear to me'),
            (r'\bthis is bad\b', 'this could be improved'),
            (r'\bI see this differently about this\b', 'I see this point differently'),
        ]
        for pattern, replacement in soften_rules:
            polished = re.sub(pattern, replacement, polished, flags=re.IGNORECASE)

        # Gentle wording upgrades for common neutral statements
        polished = re.sub(r'\bworried\b', 'concerned', polished, flags=re.IGNORECASE)
        polished = re.sub(r'\bvery\b', 'really', polished, flags=re.IGNORECASE)

        # If the input is a direct command, make it a polite request
        please_command_match = re.match(
            r'^please\s+(send|share|provide|review|check|update|fix|explain|confirm)\b(.*)$',
            polished,
            flags=re.IGNORECASE,
        )

        if please_command_match:
            verb = please_command_match.group(1).lower()
            remainder = please_command_match.group(2).strip()
            polite_map = {
                'send': 'Could you please send',
                'share': 'Could you please share',
                'provide': 'Could you please provide',
                'review': 'Could you please review',
                'check': 'Could you please check',
                'update': 'Could you please update',
                'fix': 'Could you please fix',
                'explain': 'Could you please explain',
                'confirm': 'Could you please confirm',
            }
            starter = polite_map.get(verb, 'Could you please')
            polished = f"{starter} {remainder}".strip()
            polished = re.sub(r'\s+', ' ', polished)

        command_match = re.match(
            r'^(send|share|provide|review|check|update|fix|explain|confirm)\b(.*)$',
            polished,
            flags=re.IGNORECASE,
        )
        if command_match:
            verb = command_match.group(1).lower()
            remainder = command_match.group(2).strip()
            polite_map = {
                'send': 'Could you please send',
                'share': 'Could you please share',
                'provide': 'Could you please provide',
                'review': 'Could you please review',
                'check': 'Could you please check',
                'update': 'Could you please update',
                'fix': 'Could you please fix',
                'explain': 'Could you please explain',
                'confirm': 'Could you please confirm',
            }
            starter = polite_map.get(verb, 'Could you please')
            polished = f"{starter} {verb if verb not in starter.lower() else ''} {remainder}".strip()
            polished = re.sub(r'\s+', ' ', polished)

        # Sentence-case normalization
        if source_was_upper or (polished and polished.isupper()):
            polished = polished.lower()

        # Normalize standalone lowercase "i" pronoun
        polished = re.sub(r'\bi\b', 'I', polished)

        if polished and polished[0].islower():
            polished = polished[0].upper() + polished[1:]

        # Ensure closing punctuation
        if not re.search(r'[.!?]$', polished):
            polished += '.'

        # Emotion-aware tone polishing
        tone_suffix = ''
        tone = (dominant_emotion or 'neutral').lower()

        if tone == 'anger':
            polished = re.sub(r'\bfurious\b', 'frustrated', polished, flags=re.IGNORECASE)
            polished = re.sub(r'\benraged\b', 'very upset', polished, flags=re.IGNORECASE)
        elif tone == 'sadness':
            polished = re.sub(r'\bheartbroken\b', 'deeply saddened', polished, flags=re.IGNORECASE)
        elif tone == 'fear':
            polished = re.sub(r'\bworried\b', 'concerned', polished, flags=re.IGNORECASE)
        elif tone == 'disgust':
            polished = re.sub(r'\bdisgusting\b', 'very unpleasant', polished, flags=re.IGNORECASE)
            polished = re.sub(r'\bgross\b', 'unpleasant', polished, flags=re.IGNORECASE)

        if tone == 'anger':
            tone_suffix = ' Let us address this calmly.'
        elif tone == 'fear':
            tone_suffix = ' I would appreciate some clarity and reassurance.'
        elif tone == 'sadness':
            tone_suffix = ' I hope we can handle this thoughtfully.'

        # Guarantee rewrite differs while staying natural
        if polished.strip().lower() == source.strip().lower():
            if polished.endswith('?'):
                can_you_match = re.match(r'^Can you\s+(.*)\?$', polished, flags=re.IGNORECASE)
                if can_you_match:
                    remainder = can_you_match.group(1).strip()
                    remainder = re.sub(r'^please\s+', '', remainder, flags=re.IGNORECASE)
                    polished = f"Would you be able to {remainder}?"
                else:
                    polished = 'Could you please help with this request?'
            else:
                starter_map = {
                    'anger': 'I feel frustrated, and ',
                    'fear': 'I feel concerned, and ',
                    'sadness': 'I feel saddened, and ',
                    'disgust': 'I find this unpleasant, and ',
                    'joy': 'I appreciate this, and ',
                    'neutral': 'To phrase this clearly, '
                }
                starter = starter_map.get(tone, 'To phrase this clearly, ')
                polished = starter + polished[0].lower() + polished[1:]

        is_polite_request = bool(re.match(r'^(Could you|Can you|Would you)\b', polished, flags=re.IGNORECASE))
        if tone_suffix and not is_polite_request and tone_suffix.strip().lower() not in polished.strip().lower():
            polished = polished.rstrip() + tone_suffix

        return polished