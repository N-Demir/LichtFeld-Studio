#!/bin/bash
set -e

# Check if data_folder and output_folder arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <data_folder> <output_folder>"
    echo "Example: $0 /nvs-bench/data/mipnerf360/bicycle /nvs-bench/methods/3dgs/mipnerf360/bicycle"
    exit 1
fi
data_folder=$1
output_folder=$2

######## START OF YOUR CODE ########
# 1) Train 
#   python train.py --data $data_folder --output $output_folder --eval
# 2) Render the test split
#   python render.py --data $data_folder/test --output $output_folder --eval
# 3) Move the renders into `$output_folder/test_renders`
#   mv $output_folder/test/ours_30000/renders $output_folder/test_renders

# If you want to change this, make sure
#  "eval_steps": [7000, 30000], 
# is changed in the appropriate optimization_params.json file (mcmc_... for example)
# should instead be changed to [10, 7000, 30000] for example or else no saving will happen
iterations=30000

./build/LichtFeld-Studio -d $data_folder \
    -o $output_folder \
    --eval \
    --save-eval-images \
    --render-mode RGB \
    --headless \
    --just-save-renders \
    -i $iterations

mv $output_folder/eval_step_$iterations $output_folder/test_renders