A worked serving call.

input_one_complete_lot.csv   lot A_L03, 70 components, all four epochs
output_one_complete_lot.csv  what Module A returns for it

The lot is complete - every component the manifest declares for A_L03 is present. Remove one row and the call is refused, deliberately: a lot-relative reference computed on a partial lot is wrong, not approximate.

Of these 70 components, 4 are MONITOR and 2 are CONFIRMED.
