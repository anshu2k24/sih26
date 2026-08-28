import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

class SensorSequenceDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        """
        X: (num_samples, seq_length, num_channels)
        y: (num_samples,)
        """
        self.X = torch.tensor(X, dtype=torch.float32)
        
        # PyTorch Conv1d expects (batch, channels, length)
        self.X = self.X.transpose(1, 2)
        
        self.y = torch.tensor(y, dtype=torch.float32)
        
    def __len__(self):
        return len(self.y)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class Simple1DCNN(nn.Module):
    def __init__(self, num_channels: int, seq_length: int):
        super().__init__()
        
        self.conv_block = nn.Sequential(
            nn.Conv1d(num_channels, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(0.2),
            
            nn.Conv1d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(0.2)
        )
        
        # Calculate flattened dimension
        # Assuming seq_length = 50, after two MaxPool1d(2):
        # 50 -> 25 -> 12
        flattened_len = seq_length // 4
        
        self.fc_block = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * flattened_len, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        features = self.conv_block(x)
        logits = self.fc_block(features)
        return torch.sigmoid(logits).squeeze(-1)


def extract_sequences(df_events, df_sensors, target_event='FORMATION_MUD_LOSS', horizon=25.0, seq_length=50):
    """
    Extracts sequences for both positive events and deterministic negatives.
    Returns: X (list of 2D arrays), y (list of ints), groups (list of strs)
    """
    from ertmac.ml.dataset import generate_deterministic_negatives
    
    channels = ['rop', 'wob', 'rpm', 'torque', 'hookload', 'spp', 'flow_in', 'mud_density']
    
    # Generate negatives
    df_neg = generate_deterministic_negatives(df_sensors, df_events, target_event_type=target_event, ratio=5, random_seed=42)
    
    pos_events = df_events[df_events['event_type'] == target_event].copy()
    
    X_list = []
    y_list = []
    groups = []
    
    def process_row(wb, cutoff_md, label):
        wb_sensors = df_sensors[df_sensors['wellbore_id'] == wb]
        past_sensors = wb_sensors[wb_sensors['md'] <= cutoff_md].sort_values('md')
        
        if len(past_sensors) == 0:
            return
            
        latest_md = past_sensors['md'].iloc[-1]
        assert latest_md <= cutoff_md, "Leakage detected!"
        assert (past_sensors['md'] > cutoff_md).sum() == 0, "Future data detected!"
        
        # Ensure we have recent data
        if cutoff_md - latest_md > 25.0:
            return
            
        # Extract last `seq_length` samples
        seq_data = past_sensors[channels].values
        
        if len(seq_data) >= seq_length:
            seq_data = seq_data[-seq_length:]
        else:
            # Pad with first value
            pad_len = seq_length - len(seq_data)
            pad_val = seq_data[0]
            padding = np.tile(pad_val, (pad_len, 1))
            seq_data = np.vstack([padding, seq_data])
            
        X_list.append(seq_data)
        y_list.append(label)
        
        # Determine group
        group = wb.split("-")[0] + "-" + wb.split("-")[1] if "-" in str(wb) else str(wb)
        groups.append(group)

    for _, row in pos_events.iterrows():
        cutoff = row['md'] - horizon
        process_row(row['wellbore_id'], cutoff, 1)
        
    for _, row in df_neg.iterrows():
        cutoff = row['md']
        process_row(row['wellbore_id'], cutoff, 0)
        
    return np.array(X_list), np.array(y_list), np.array(groups)


def fit_predict_cnn(X_train, y_train, X_test, epochs=30, batch_size=16, per_sample_norm=False):
    """
    Standardize channels.
    Train CNN, predict on X_train and X_test.
    """
    # X shape: (samples, seq_length, channels)
    num_channels = X_train.shape[2]
    seq_length = X_train.shape[1]
    
    if per_sample_norm:
        # Normalize each sample independently (time dimension)
        tr_m = np.nanmean(X_train, axis=1, keepdims=True)
        tr_s = np.nanstd(X_train, axis=1, keepdims=True)
        tr_s[tr_s == 0] = 1e-6
        X_train_norm = (X_train - tr_m) / tr_s
        
        te_m = np.nanmean(X_test, axis=1, keepdims=True)
        te_s = np.nanstd(X_test, axis=1, keepdims=True)
        te_s[te_s == 0] = 1e-6
        X_test_norm = (X_test - te_m) / te_s
    else:
        # 1. Normalize based on Train ONLY
        train_means = np.nanmean(X_train, axis=(0, 1))
        train_stds = np.nanstd(X_train, axis=(0, 1))
        
        # Avoid div by zero
        train_stds[train_stds == 0] = 1e-6
        
        X_train_norm = (X_train - train_means) / train_stds
        X_test_norm = (X_test - train_means) / train_stds
    
    # Replace any remaining NaNs with 0
    X_train_norm = np.nan_to_num(X_train_norm)
    X_test_norm = np.nan_to_num(X_test_norm)
    
    # Calculate scale_pos_weight for imbalance
    pos_count = np.sum(y_train == 1)
    neg_count = np.sum(y_train == 0)
    pos_weight = neg_count / max(pos_count, 1)
    
    dataset = SensorSequenceDataset(X_train_norm, y_train)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    model = Simple1DCNN(num_channels=num_channels, seq_length=seq_length)
    
    # Binary Cross Entropy with pos_weight
    criterion = nn.BCELoss(weight=None) 
    # To use pos_weight safely, we apply it per sample
    
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    model.train()
    for epoch in range(epochs):
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            preds = model(batch_X)
            
            # Apply pos weight manually
            weights = torch.ones_like(batch_y)
            weights[batch_y == 1] = pos_weight
            
            loss = nn.BCELoss(weight=weights)(preds, batch_y)
            loss.backward()
            optimizer.step()
            
    model.eval()
    with torch.no_grad():
        # Predict Train
        ds_train = SensorSequenceDataset(X_train_norm, y_train)
        dl_train = DataLoader(ds_train, batch_size=64, shuffle=False)
        train_preds = []
        for b_x, _ in dl_train:
            train_preds.extend(model(b_x).numpy())
            
        # Predict Test
        ds_test = SensorSequenceDataset(X_test_norm, np.zeros(len(X_test_norm)))
        dl_test = DataLoader(ds_test, batch_size=64, shuffle=False)
        test_preds = []
        for b_x, _ in dl_test:
            test_preds.extend(model(b_x).numpy())
            
    return np.array(train_preds), np.array(test_preds)
