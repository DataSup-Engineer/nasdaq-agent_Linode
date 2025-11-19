"""
Natural Language Processing service for NASDAQ Stock Agent
Handles company name to ticker symbol resolution with fuzzy matching
"""
import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CompanyMatch:
    """Represents a company name match result"""
    ticker: str
    company_name: str
    match_score: float
    match_type: str  # 'exact', 'partial', 'fuzzy', 'alias'


class CompanyNameResolver:
    """Resolves company names to NASDAQ ticker symbols with fuzzy matching"""
    
    def __init__(self):
        # Initialize common_words first as it's used by other methods
        self.common_words = {'inc', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited', 'llc', 'the'}
        self.company_database = self._build_company_database()
        self.aliases = self._build_alias_database()
    
    def _build_company_database(self) -> Dict[str, Dict[str, str]]:
        """Build comprehensive NASDAQ company database"""
        return {
            # Technology Companies
            'aapl': {
                'ticker': 'AAPL',
                'name': 'Apple Inc.',
                'aliases': ['apple', 'apple computer', 'apple inc']
            },
            'msft': {
                'ticker': 'MSFT', 
                'name': 'Microsoft Corporation',
                'aliases': ['microsoft', 'microsoft corp', 'msft']
            },
            'googl': {
                'ticker': 'GOOGL',
                'name': 'Alphabet Inc.',
                'aliases': ['google', 'alphabet', 'alphabet inc', 'google inc']
            },
            'amzn': {
                'ticker': 'AMZN',
                'name': 'Amazon.com Inc.',
                'aliases': ['amazon', 'amazon.com', 'amazon inc']
            },
            'tsla': {
                'ticker': 'TSLA',
                'name': 'Tesla Inc.',
                'aliases': ['tesla', 'tesla motors', 'tesla inc']
            },
            'meta': {
                'ticker': 'META',
                'name': 'Meta Platforms Inc.',
                'aliases': ['meta', 'facebook', 'meta platforms', 'facebook inc']
            },
            'nflx': {
                'ticker': 'NFLX',
                'name': 'Netflix Inc.',
                'aliases': ['netflix', 'netflix inc']
            },
            'nvda': {
                'ticker': 'NVDA',
                'name': 'NVIDIA Corporation',
                'aliases': ['nvidia', 'nvidia corp', 'nvidia corporation']
            },
            'intc': {
                'ticker': 'INTC',
                'name': 'Intel Corporation',
                'aliases': ['intel', 'intel corp', 'intel corporation']
            },
            'csco': {
                'ticker': 'CSCO',
                'name': 'Cisco Systems Inc.',
                'aliases': ['cisco', 'cisco systems', 'cisco inc']
            },
            'orcl': {
                'ticker': 'ORCL',
                'name': 'Oracle Corporation',
                'aliases': ['oracle', 'oracle corp', 'oracle corporation']
            },
            'crm': {
                'ticker': 'CRM',
                'name': 'Salesforce Inc.',
                'aliases': ['salesforce', 'salesforce.com', 'salesforce inc']
            },
            'adbe': {
                'ticker': 'ADBE',
                'name': 'Adobe Inc.',
                'aliases': ['adobe', 'adobe systems', 'adobe inc']
            },
            'pypl': {
                'ticker': 'PYPL',
                'name': 'PayPal Holdings Inc.',
                'aliases': ['paypal', 'paypal holdings', 'paypal inc']
            },
            'zm': {
                'ticker': 'ZM',
                'name': 'Zoom Video Communications Inc.',
                'aliases': ['zoom', 'zoom video', 'zoom communications']
            },
            'spot': {
                'ticker': 'SPOT',
                'name': 'Spotify Technology S.A.',
                'aliases': ['spotify', 'spotify technology']
            },
            'uber': {
                'ticker': 'UBER',
                'name': 'Uber Technologies Inc.',
                'aliases': ['uber', 'uber technologies', 'uber inc']
            },
            'lyft': {
                'ticker': 'LYFT',
                'name': 'Lyft Inc.',
                'aliases': ['lyft', 'lyft inc']
            },
            'abnb': {
                'ticker': 'ABNB',
                'name': 'Airbnb Inc.',
                'aliases': ['airbnb', 'airbnb inc', 'air bnb']
            },
            'dash': {
                'ticker': 'DASH',
                'name': 'DoorDash Inc.',
                'aliases': ['doordash', 'door dash', 'doordash inc']
            },
            'snow': {
                'ticker': 'SNOW',
                'name': 'Snowflake Inc.',
                'aliases': ['snowflake', 'snowflake inc']
            },
            'pltr': {
                'ticker': 'PLTR',
                'name': 'Palantir Technologies Inc.',
                'aliases': ['palantir', 'palantir technologies', 'palantir inc']
            },
            'hood': {
                'ticker': 'HOOD',
                'name': 'Robinhood Markets Inc.',
                'aliases': ['robinhood', 'robinhood markets', 'robin hood']
            },
            
            # Biotech/Healthcare
            'mrna': {
                'ticker': 'MRNA',
                'name': 'Moderna Inc.',
                'aliases': ['moderna', 'moderna inc']
            },
            'bntx': {
                'ticker': 'BNTX',
                'name': 'BioNTech SE',
                'aliases': ['biontech', 'biontech se']
            },
            'gild': {
                'ticker': 'GILD',
                'name': 'Gilead Sciences Inc.',
                'aliases': ['gilead', 'gilead sciences']
            },
            
            # Retail/Consumer
            'cost': {
                'ticker': 'COST',
                'name': 'Costco Wholesale Corporation',
                'aliases': ['costco', 'costco wholesale']
            },
            'sbux': {
                'ticker': 'SBUX',
                'name': 'Starbucks Corporation',
                'aliases': ['starbucks', 'starbucks corp']
            },
            
            # Semiconductor
            'amd': {
                'ticker': 'AMD',
                'name': 'Advanced Micro Devices Inc.',
                'aliases': ['amd', 'advanced micro devices']
            },
            'qcom': {
                'ticker': 'QCOM',
                'name': 'QUALCOMM Incorporated',
                'aliases': ['qualcomm', 'qualcomm inc']
            },
            'avgo': {
                'ticker': 'AVGO',
                'name': 'Broadcom Inc.',
                'aliases': ['broadcom', 'broadcom inc']
            }
        }
    
    def _build_alias_database(self) -> Dict[str, str]:
        """Build reverse lookup for aliases to tickers"""
        alias_db = {}
        
        for ticker_key, company_data in self.company_database.items():
            ticker = company_data['ticker']
            
            # Add company name
            clean_name = self._clean_company_name(company_data['name'])
            alias_db[clean_name] = ticker
            
            # Add all aliases
            for alias in company_data['aliases']:
                clean_alias = self._clean_company_name(alias)
                alias_db[clean_alias] = ticker
        
        return alias_db
    
    def _clean_company_name(self, name: str) -> str:
        """Clean and normalize company name for matching"""
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common punctuation
        name = re.sub(r'[.,\-_()&]', ' ', name)
        
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Remove common corporate suffixes
        words = name.split()
        filtered_words = [word for word in words if word not in self.common_words]
        
        return ' '.join(filtered_words) if filtered_words else name
    
    async def resolve_company_name(self, query: str) -> List[CompanyMatch]:
        """Resolve company name to ticker symbols with confidence scoring"""
        if not query or not query.strip():
            return []
        
        query = query.strip()
        clean_query = self._clean_company_name(query)
        
        matches = []
        
        # 1. Exact match (highest priority)
        exact_matches = self._find_exact_matches(clean_query)
        matches.extend(exact_matches)
        
        # 2. Partial matches
        if not exact_matches:
            partial_matches = self._find_partial_matches(clean_query)
            matches.extend(partial_matches)
        
        # 3. Fuzzy matches (if no exact or partial matches)
        if not matches:
            fuzzy_matches = self._find_fuzzy_matches(clean_query)
            matches.extend(fuzzy_matches)
        
        # 4. Check if query is already a ticker
        ticker_match = self._check_if_ticker(query.upper())
        if ticker_match:
            matches.insert(0, ticker_match)  # Prioritize direct ticker matches
        
        # Sort by match score and remove duplicates
        unique_matches = self._deduplicate_matches(matches)
        sorted_matches = sorted(unique_matches, key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"Resolved '{query}' to {len(sorted_matches)} matches")
        return sorted_matches[:5]  # Return top 5 matches
    
    def _find_exact_matches(self, clean_query: str) -> List[CompanyMatch]:
        """Find exact matches in the alias database"""
        matches = []
        
        if clean_query in self.aliases:
            ticker = self.aliases[clean_query]
            company_data = self._get_company_data_by_ticker(ticker)
            
            if company_data:
                matches.append(CompanyMatch(
                    ticker=ticker,
                    company_name=company_data['name'],
                    match_score=1.0,
                    match_type='exact'
                ))
        
        return matches
    
    def _find_partial_matches(self, clean_query: str) -> List[CompanyMatch]:
        """Find partial matches in company names and aliases"""
        matches = []
        
        for alias, ticker in self.aliases.items():
            # Check if query is contained in alias or vice versa
            if (clean_query in alias or alias in clean_query) and len(clean_query) > 2:
                company_data = self._get_company_data_by_ticker(ticker)
                
                if company_data:
                    # Calculate match score based on length similarity
                    score = min(len(clean_query), len(alias)) / max(len(clean_query), len(alias))
                    score = max(0.6, score)  # Minimum score for partial matches
                    
                    matches.append(CompanyMatch(
                        ticker=ticker,
                        company_name=company_data['name'],
                        match_score=score,
                        match_type='partial'
                    ))
        
        return matches
    
    def _find_fuzzy_matches(self, clean_query: str) -> List[CompanyMatch]:
        """Find fuzzy matches using string similarity"""
        matches = []
        
        for alias, ticker in self.aliases.items():
            similarity = SequenceMatcher(None, clean_query, alias).ratio()
            
            if similarity >= 0.6:  # Minimum similarity threshold
                company_data = self._get_company_data_by_ticker(ticker)
                
                if company_data:
                    matches.append(CompanyMatch(
                        ticker=ticker,
                        company_name=company_data['name'],
                        match_score=similarity,
                        match_type='fuzzy'
                    ))
        
        return matches
    
    def _check_if_ticker(self, query: str) -> Optional[CompanyMatch]:
        """Check if the query is already a valid ticker symbol"""
        if len(query) <= 5 and query.isalpha():
            company_data = self._get_company_data_by_ticker(query)
            
            if company_data:
                return CompanyMatch(
                    ticker=query,
                    company_name=company_data['name'],
                    match_score=1.0,
                    match_type='ticker'
                )
        
        return None
    
    def _get_company_data_by_ticker(self, ticker: str) -> Optional[Dict[str, str]]:
        """Get company data by ticker symbol"""
        ticker_key = ticker.lower()
        return self.company_database.get(ticker_key)
    
    def _deduplicate_matches(self, matches: List[CompanyMatch]) -> List[CompanyMatch]:
        """Remove duplicate matches, keeping the highest scoring one"""
        seen_tickers = {}
        
        for match in matches:
            if match.ticker not in seen_tickers or match.match_score > seen_tickers[match.ticker].match_score:
                seen_tickers[match.ticker] = match
        
        return list(seen_tickers.values())
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker exists in our database"""
        if not ticker:
            return False
        
        return self._get_company_data_by_ticker(ticker.upper()) is not None
    
    async def get_company_info(self, ticker: str) -> Optional[Dict[str, str]]:
        """Get company information by ticker"""
        return self._get_company_data_by_ticker(ticker.upper())
    
    async def suggest_alternatives(self, invalid_query: str) -> List[CompanyMatch]:
        """Suggest alternative company names for invalid queries"""
        # Use fuzzy matching with lower threshold for suggestions
        clean_query = self._clean_company_name(invalid_query)
        suggestions = []
        
        for alias, ticker in self.aliases.items():
            similarity = SequenceMatcher(None, clean_query, alias).ratio()
            
            if similarity >= 0.4:  # Lower threshold for suggestions
                company_data = self._get_company_data_by_ticker(ticker)
                
                if company_data:
                    suggestions.append(CompanyMatch(
                        ticker=ticker,
                        company_name=company_data['name'],
                        match_score=similarity,
                        match_type='suggestion'
                    ))
        
        # Sort by similarity and return top suggestions
        suggestions.sort(key=lambda x: x.match_score, reverse=True)
        return suggestions[:3]  # Return top 3 suggestions


class NLPService:
    """High-level NLP service for the NASDAQ Stock Agent"""
    
    def __init__(self):
        self.company_resolver = CompanyNameResolver()
    
    async def process_stock_query(self, query: str) -> Dict[str, any]:
        """Process a natural language stock query"""
        try:
            # Clean and validate input
            if not query or not query.strip():
                return {
                    'success': False,
                    'error': 'Empty query provided',
                    'suggestions': []
                }
            
            query = query.strip()
            
            # Resolve company name to ticker
            matches = await self.company_resolver.resolve_company_name(query)
            
            if not matches:
                # No matches found, provide suggestions
                suggestions = await self.company_resolver.suggest_alternatives(query)
                return {
                    'success': False,
                    'error': f'No matches found for "{query}"',
                    'suggestions': [
                        {
                            'ticker': match.ticker,
                            'company_name': match.company_name,
                            'match_score': match.match_score
                        }
                        for match in suggestions
                    ]
                }
            
            # Return the best match
            best_match = matches[0]
            
            return {
                'success': True,
                'ticker': best_match.ticker,
                'company_name': best_match.company_name,
                'match_score': best_match.match_score,
                'match_type': best_match.match_type,
                'alternative_matches': [
                    {
                        'ticker': match.ticker,
                        'company_name': match.company_name,
                        'match_score': match.match_score,
                        'match_type': match.match_type
                    }
                    for match in matches[1:]
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to process stock query '{query}': {e}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}',
                'suggestions': []
            }
    
    async def validate_and_resolve_ticker(self, input_text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate input and resolve to ticker if needed"""
        try:
            result = await self.process_stock_query(input_text)
            
            if result['success']:
                return True, result['ticker'], result['company_name']
            else:
                return False, None, result.get('error', 'Unknown error')
                
        except Exception as e:
            logger.error(f"Failed to validate and resolve '{input_text}': {e}")
            return False, None, str(e)


# Global NLP service instance
nlp_service = NLPService()