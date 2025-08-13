from db.nsfw_detector import NSFWDetector
import sys
import time
from colorama import init, Fore, Style

init()

def print_results(result, threshold):
    if 'error' in result and result['error']:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} {result['error']}")
        return
    
    print(f"\n{Fore.BLUE}Results:{Style.RESET_ALL}")
    for cls, percent in sorted(result['scores'].items(),
                             key=lambda x: x[1], reverse=True):
        if cls == 'safe':
            color = Fore.GREEN
        elif cls in ['porn','hentai'] and percent > threshold*100:
            color = Fore.RED
        else:
            color = Fore.YELLOW
        print(f"{color}{cls.upper()+':':<10} {percent}%{Style.RESET_ALL}")
    
    nsfw_score = max(result['scores']['porn'], result['scores']['hentai'])
    conclusion = "NSFW" if result['is_nsfw'] else "Safe"
    color = Fore.RED if result['is_nsfw'] else Fore.GREEN
    
    print(f"\n{Fore.YELLOW}NSFW Confidence:{Style.RESET_ALL} {nsfw_score}%")
    print(f"{color}Conclusion: {conclusion}{Style.RESET_ALL} (Threshold: {threshold*100}%)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test.py <image.jpg> [threshold=0.8]")
        sys.exit(1)
    
    threshold =  0.8
    
    print("Initializing Enhanced NSFW Detector...")
    start_time = time.time()
    
    try:
        detector = NSFWDetector()
        print(f"Loaded in {time.time()-start_time:.2f}s")
        
        print(f"\nAnalyzing {sys.argv[1]}...")
        result = detector.predict(sys.argv[1], threshold)
        print_results(result, threshold)
        
    except Exception as e:
        print(f"{Fore.RED}Failed:{Style.RESET_ALL} {str(e)}")
        sys.exit(1)