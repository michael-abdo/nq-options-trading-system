
import sys
sys.path.insert(0, '.')

# Try to import various symbol generators that might exist
symbol_generators = []

try:
    from tasks.options_trading_system.data_ingestion.barchart_web_scraper.symbol_generator import BarchartSymbolGenerator
    sg = BarchartSymbolGenerator()
    symbol_generators.append(('BarchartSymbolGenerator', lambda b, o, y: sg.get_eod_contract_symbol(b, o, y)))
except ImportError:
    pass

try:
    from tasks.options_trading_system.data_ingestion.barchart_web_scraper.solution import BarchartAPIComparator
    comp = BarchartAPIComparator()
    symbol_generators.append(('BarchartAPIComparator', lambda b, o, y: comp.get_eod_contract_symbol(b, o, y)))
except ImportError:
    pass

# Test each generator
test_cases = [('NQ', 'weekly', '2digit'), ('NQ', 'monthly', '2digit'), ('NQ', 'friday', '2digit'), ('NQ', 'daily', '2digit')]
for base, opt_type, year_fmt in test_cases:
    print(f"\nTesting: {base}, {opt_type}, {year_fmt}")
    for name, generator in symbol_generators:
        try:
            result = generator(base, opt_type, year_fmt)
            print(f"  {name}: {result}")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
