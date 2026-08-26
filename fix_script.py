import re

with open("scripts/build_sensor_dataset.py", "r") as f:
    content = f.read()

# Fix the positive loop
content = content.replace("if wb not in usrop_wells:", "norm_wb = wb.replace('NO ', '')\n        if norm_wb not in usrop_wells:")
content = content.replace("wb_data = df_usrop[df_usrop['well_id'] == wb]", "wb_data = df_usrop[df_usrop['well_id'] == norm_wb]")

# Fix the negative loop
content = content.replace("if wb not in usrop_wells: continue", "norm_wb = wb.replace('NO ', '')\n        if norm_wb not in usrop_wells: continue")
content = content.replace("wb_data = df_usrop[df_usrop['well_id'] == wb]", "wb_data = df_usrop[df_usrop['well_id'] == norm_wb]")
content = content.replace("row_dict['example_id'] = f\"NEG_{wb}_{i}_H{h}\"", "row_dict['example_id'] = f\"NEG_{norm_wb}_{i}_H{h}\"")

with open("scripts/build_sensor_dataset.py", "w") as f:
    f.write(content)
