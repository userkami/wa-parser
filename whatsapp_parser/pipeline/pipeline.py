from typing import Dict, Any
from .base import ModuleError, ErrorLog, ErrorLevel
from .file_loader import FileLoader
from .message_splitter import MessageSplitter
from .normalizer import Normalizer
from .classifier import MessageClassifier
from .multi_offer_splitter import MultiOfferSplitter
from .extractor import FieldExtractor
from .pkr_normalizer import PKRNormalizer
from .deduper import Deduper
from .confidence_scorer import ConfidenceScorer
from .exporter import Exporter
from .dictionary_manager import DictionaryManager


class ParsingPipeline:
    """
    Main pipeline coordinator that orchestrates all parsing modules.
    """
    
    def __init__(self):
        self.dict_mgr = DictionaryManager()
        self.error_log = None
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Execute the full parsing pipeline.
        
        Returns:
            payload with all results
        """
        payload = {'file_path': file_path}
        
        try:
            print("[1/11] Loading file...")
            loader = FileLoader()
            payload = loader.process(payload)
            
            # Create error log for this import
            self.error_log = ErrorLog(payload.get('import_id', ''))
            
            print("[2/11] Detecting format and splitting messages...")
            splitter = MessageSplitter(self.error_log)
            payload = splitter.process(payload)
            
            print("[3/11] Normalizing text...")
            normalizer = Normalizer(self.dict_mgr)
            payload = normalizer.process(payload)
            
            print("[4/11] Classifying messages...")
            classifier = MessageClassifier(self.dict_mgr)
            payload = classifier.process(payload)
            
            print("[5/11] Detecting multi-offer messages...")
            multi_splitter = MultiOfferSplitter(self.dict_mgr)
            payload = multi_splitter.process(payload)
            
            print("[6/11] Extracting structured fields...")
            extractor = FieldExtractor(self.dict_mgr)
            payload = extractor.process(payload)
            
            print("[7/11] Normalizing prices to PKR...")
            pkr_norm = PKRNormalizer()
            payload = pkr_norm.process(payload)
            
            print("[8/11] Detecting duplicates...")
            deduper = Deduper()
            payload = deduper.process(payload)
            
            print("[9/11] Calculating confidence scores...")
            scorer = ConfidenceScorer()
            payload = scorer.process(payload)
            
            print("[10/11] Exporting results...")
            exporter = Exporter()
            payload = exporter.process(payload)
            
            payload['parsing_status'] = 'success'
            payload['error_log'] = self.error_log
            
            return payload
        
        except ModuleError as e:
            if self.error_log:
                self.error_log.add_error(e)
            
            if e.level == ErrorLevel.FATAL:
                payload['parsing_status'] = 'failed'
                payload['error_message'] = e.message
                return payload
            
            # Continue with partial import
            payload['parsing_status'] = 'partial'
            payload['error_log'] = self.error_log
            return payload
        
        except Exception as e:
            payload['parsing_status'] = 'error'
            payload['error_message'] = str(e)
            return payload
