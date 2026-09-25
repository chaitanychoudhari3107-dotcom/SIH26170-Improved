import sys
sys.path.insert(0, ".")
from data_loader import *

print(f"Fusion: {len(fusion_df)} rows")
print(f"Module A epochs: {list(module_a_dfs.keys())}")
print(f"Module B: {len(module_b_df)} rows")

c = get_component("C00158")
print(f"C00158 disposition: {c['module_a']['disposition']}")
print(f"C00158 tier: {c['module_a']['evidence_tier']}")
print(f"C00158 B primary: {c['module_b']['primary_parameter']}")
print(f"C00158 IDDQ pred: {c['module_b']['predictions']['IDDQ']}")

s = get_summary()
print(f"Summary: {s}")

sr = search_components("C001")
print(f"Search 'C001': {len(sr)} results")
print(f"First: {sr[0] if sr else 'none'}")
