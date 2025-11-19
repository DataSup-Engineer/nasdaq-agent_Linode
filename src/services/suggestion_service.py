"""
Suggestion service for handling invalid queries and providing alternatives
"""
import re
from typing import List, Dict, Set
from difflib import get_close_matches
import logging
from src.services.nlp_service import CompanyMatch, CompanyNameResolver

logger = logging.getLogger(__name__)


class QuerySuggestionService:
    """Service for providing intelligent suggestions for invalid or ambiguous queries"""
    
    def __init__(self, company_resolver: CompanyNameResolver):
        self.company_resolver = company_resolver
        self.common_misspellings = self._build_misspelling_database()
        self.query_patterns = self._build_query_patterns()
    
    def _build_misspelling_database(self) -> Dict[str, str]:
        """Build database of common company name misspellings"""
        return {
            # Common misspellings
            'appl': 'apple',
            'aple': 'apple',
            'appel': 'apple',
            'microsft': 'microsoft',
            'microsofy': 'microsoft',
            'micorsoft': 'microsoft',
            'gogle': 'google',
            'googel': 'google',
            'gooogle': 'google',
            'amazn': 'amazon',
            'amzon': 'amazon',
            'amazom': 'amazon',
            'tesls': 'tesla',
            'telsa': 'tesla',
            'teslaa': 'tesla',
            'facbook': 'facebook',
            'facebok': 'facebook',
            'facebuk': 'facebook',
            'netfix': 'netflix',
            'netflex': 'netflix',
            'netflx': 'netflix',
            'nvidea': 'nvidia',
            'nviida': 'nvidia',
            'nvida': 'nvidia',
            'payapl': 'paypal',
            'paypl': 'paypal',
            'paypall': 'paypal',
            'spotfy': 'spotify',
            'spotifi': 'spotify',
            'spotigy': 'spotify',
            'uberr': 'uber',
            'ubber': 'uber',
            'airbnbb': 'airbnb',
            'airbmb': 'airbnb',
            'airbb': 'airbnb'
        }
    
    def _build_query_patterns(self) -> List[Dict[str, str]]:
        """Build patterns for common query formats"""
        return [
            {
                'pattern': r'what.*about\s+(.+)',
                'description': 'Questions about companies',
                'example': 'What do you think about Apple?'
            },
            {
                'pattern': r'how.*is\s+(.+)\s+doing',
                'description': 'Performance questions',
                'example': 'How is Microsoft doing?'
            },
            {
                'pattern': r'should.*buy\s+(.+)',
                'description': 'Investment advice questions',
                'example': 'Should I buy Tesla stock?'
            },
            {
                'pattern': r'(.+)\s+stock\s+price',
                'description': 'Stock price queries',
                'example': 'Apple stock price'
            },
            {
                'pattern': r'analyze\s+(.+)',
                'description': 'Analysis requests',
                'example': 'Analyze Amazon'
            }
        ]
    
    async def suggest_corrections(self, invalid_query: str) -> Dict[str, any]:
        """Provide intelligent suggestions for invalid queries"""
        try:
            suggestions = {
                'original_query': invalid_query,
                'corrected_queries': [],
                'similar_companies': [],
                'query_improvements': [],
                'common_mistakes': []
            }
            
            # 1. Check for common misspellings
            misspelling_corrections = self._check_misspellings(invalid_query)
            if misspelling_corrections:
                suggestions['corrected_queries'].extend(misspelling_corrections)
            
            # 2. Extract company name from query patterns
            extracted_companies = self._extract_company_from_patterns(invalid_query)
            for company in extracted_companies:
                company_suggestions = await self.company_resolver.suggest_alternatives(company)
                suggestions['similar_companies'].extend([
                    {
                        'ticker': match.ticker,
                        'company_name': match.company_name,
                        'match_score': match.match_score,
                        'extracted_from': company
                    }
                    for match in company_suggestions
                ])
            
            # 3. Provide query format suggestions
            format_suggestions = self._suggest_query_formats(invalid_query)
            suggestions['query_improvements'].extend(format_suggestions)
            
            # 4. Check for common mistakes
            common_mistakes = self._identify_common_mistakes(invalid_query)
            suggestions['common_mistakes'].extend(common_mistakes)
            
            # 5. Fuzzy matching against all known company names
            if not suggestions['similar_companies']:
                fuzzy_matches = await self._fuzzy_match_all_companies(invalid_query)
                suggestions['similar_companies'].extend(fuzzy_matches)
            
            logger.info(f"Generated suggestions for invalid query: '{invalid_query}'")
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions for '{invalid_query}': {e}")
            return {
                'original_query': invalid_query,
                'error': str(e),
                'corrected_queries': [],
                'similar_companies': [],
                'query_improvements': [],
                'common_mistakes': []
            }
    
    def _check_misspellings(self, query: str) -> List[str]:
        """Check for and correct common misspellings"""
        corrections = []
        query_lower = query.lower()
        
        for misspelling, correction in self.common_misspellings.items():
            if misspelling in query_lower:
                corrected_query = query_lower.replace(misspelling, correction)
                corrections.append(corrected_query.title())
        
        return corrections
    
    def _extract_company_from_patterns(self, query: str) -> List[str]:
        """Extract potential company names from query patterns"""
        extracted = []
        
        for pattern_info in self.query_patterns:
            pattern = pattern_info['pattern']
            match = re.search(pattern, query.lower())
            
            if match:
                company_part = match.group(1).strip()
                # Clean up the extracted company name
                company_part = re.sub(r'\s+stock.*', '', company_part)
                company_part = re.sub(r'\s+shares.*', '', company_part)
                company_part = company_part.strip()
                
                if company_part and len(company_part) > 1:
                    extracted.append(company_part)
        
        # Also try to extract any capitalized words (likely company names)
        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', query)
        extracted.extend(capitalized_words)
        
        return list(set(extracted))  # Remove duplicates
    
    def _suggest_query_formats(self, query: str) -> List[Dict[str, str]]:
        """Suggest better query formats"""
        suggestions = []
        
        # If query is very short, suggest more specific formats
        if len(query.strip()) < 3:
            suggestions.append({
                'suggestion': 'Try using a full company name like "Apple" or "Microsoft"',
                'example': 'Apple',
                'reason': 'Query too short'
            })
        
        # If query contains no recognizable company names
        if not re.search(r'\b[A-Z][a-z]+\b', query):
            suggestions.append({
                'suggestion': 'Include a company name in your query',
                'example': 'What do you think about Tesla?',
                'reason': 'No company name detected'
            })
        
        # If query is a question but doesn't mention a company clearly
        if '?' in query and len(query.split()) > 3:
            suggestions.append({
                'suggestion': 'Try a simpler format with just the company name',
                'example': 'Netflix',
                'reason': 'Complex question format'
            })
        
        return suggestions
    
    def _identify_common_mistakes(self, query: str) -> List[Dict[str, str]]:
        """Identify common mistakes in queries"""
        mistakes = []
        
        # Check for ticker-like strings that might be misspelled
        potential_tickers = re.findall(r'\b[A-Z]{2,5}\b', query)
        for ticker in potential_tickers:
            # Use synchronous validation for this context
            if not self.company_resolver._get_company_data_by_ticker(ticker):
                mistakes.append({
                    'mistake': f"'{ticker}' is not a valid ticker symbol",
                    'suggestion': f"Try the full company name instead of '{ticker}'",
                    'type': 'invalid_ticker'
                })
        
        # Check for numbers (might be trying to include price or dates)
        if re.search(r'\d+', query):
            mistakes.append({
                'mistake': 'Query contains numbers',
                'suggestion': 'Focus on the company name only, without prices or dates',
                'type': 'contains_numbers'
            })
        
        # Check for very long queries
        if len(query.split()) > 10:
            mistakes.append({
                'mistake': 'Query is very long',
                'suggestion': 'Try a shorter query with just the company name',
                'type': 'too_long'
            })
        
        return mistakes
    
    async def _fuzzy_match_all_companies(self, query: str) -> List[Dict[str, any]]:
        """Perform fuzzy matching against all known companies"""
        matches = []
        
        # Get all company names and aliases
        all_names = []
        for company_data in self.company_resolver.company_database.values():
            all_names.append(company_data['name'])
            all_names.extend(company_data['aliases'])
        
        # Use difflib to find close matches
        close_matches = get_close_matches(
            query.lower(), 
            [name.lower() for name in all_names], 
            n=5, 
            cutoff=0.4
        )
        
        for match in close_matches:
            # Find the ticker for this match
            ticker = None
            for alias, tick in self.company_resolver.aliases.items():
                if alias == match:
                    ticker = tick
                    break
            
            if ticker:
                company_data = self.company_resolver._get_company_data_by_ticker(ticker)
                if company_data:
                    matches.append({
                        'ticker': ticker,
                        'company_name': company_data['name'],
                        'match_score': 0.6,  # Approximate score for fuzzy matches
                        'matched_text': match
                    })
        
        return matches
    
    async def get_popular_suggestions(self) -> List[Dict[str, str]]:
        """Get a list of popular/common company suggestions"""
        popular_companies = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
            'META', 'NFLX', 'NVDA', 'PYPL', 'ZOOM'
        ]
        
        suggestions = []
        for ticker in popular_companies:
            company_data = self.company_resolver._get_company_data_by_ticker(ticker)
            if company_data:
                suggestions.append({
                    'ticker': ticker,
                    'company_name': company_data['name'],
                    'category': 'popular'
                })
        
        return suggestions
    
    async def analyze_query_intent(self, query: str) -> Dict[str, any]:
        """Analyze the intent behind a user query"""
        intent_analysis = {
            'query': query,
            'detected_intent': 'unknown',
            'confidence': 0.0,
            'extracted_entities': [],
            'suggested_action': ''
        }
        
        query_lower = query.lower()
        
        # Detect different types of intents
        if any(word in query_lower for word in ['buy', 'purchase', 'invest']):
            intent_analysis['detected_intent'] = 'investment_advice'
            intent_analysis['confidence'] = 0.8
            intent_analysis['suggested_action'] = 'Provide investment recommendation'
        
        elif any(word in query_lower for word in ['price', 'cost', 'value']):
            intent_analysis['detected_intent'] = 'price_inquiry'
            intent_analysis['confidence'] = 0.7
            intent_analysis['suggested_action'] = 'Show current stock price'
        
        elif any(word in query_lower for word in ['analyze', 'analysis', 'review']):
            intent_analysis['detected_intent'] = 'analysis_request'
            intent_analysis['confidence'] = 0.9
            intent_analysis['suggested_action'] = 'Provide comprehensive stock analysis'
        
        elif any(word in query_lower for word in ['performance', 'doing', 'trend']):
            intent_analysis['detected_intent'] = 'performance_inquiry'
            intent_analysis['confidence'] = 0.7
            intent_analysis['suggested_action'] = 'Show performance metrics and trends'
        
        # Extract potential company names
        extracted_companies = self._extract_company_from_patterns(query)
        intent_analysis['extracted_entities'] = extracted_companies
        
        return intent_analysis


# Enhanced NLP service with suggestions
class EnhancedNLPService:
    """Enhanced NLP service with comprehensive suggestion capabilities"""
    
    def __init__(self):
        self.company_resolver = CompanyNameResolver()
        self.suggestion_service = QuerySuggestionService(self.company_resolver)
    
    async def process_query_with_suggestions(self, query: str) -> Dict[str, any]:
        """Process query and provide suggestions if resolution fails"""
        try:
            # First try normal resolution
            matches = await self.company_resolver.resolve_company_name(query)
            
            if matches and matches[0].match_score >= 0.6:
                # Good match found
                best_match = matches[0]
                return {
                    'success': True,
                    'ticker': best_match.ticker,
                    'company_name': best_match.company_name,
                    'match_score': best_match.match_score,
                    'match_type': best_match.match_type,
                    'alternatives': [
                        {
                            'ticker': m.ticker,
                            'company_name': m.company_name,
                            'match_score': m.match_score
                        } for m in matches[1:3]  # Show top 2 alternatives
                    ]
                }
            
            else:
                # No good match, provide comprehensive suggestions
                suggestions = await self.suggestion_service.suggest_corrections(query)
                intent_analysis = await self.suggestion_service.analyze_query_intent(query)
                
                return {
                    'success': False,
                    'error': f'Could not resolve "{query}" to a known company',
                    'suggestions': suggestions,
                    'intent_analysis': intent_analysis,
                    'popular_companies': await self.suggestion_service.get_popular_suggestions()
                }
        
        except Exception as e:
            logger.error(f"Failed to process query with suggestions '{query}': {e}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}',
                'suggestions': {},
                'popular_companies': []
            }


# Global enhanced NLP service instance
enhanced_nlp_service = EnhancedNLPService()