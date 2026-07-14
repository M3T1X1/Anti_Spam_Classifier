import torch
print(f"Is ROCm available? {torch.cuda.is_available()}")
print(torch.version.hip)



