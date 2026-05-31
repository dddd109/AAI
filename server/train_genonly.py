"""Generator-only VITS fine-tuning — no discriminator needed."""
import os, sys, json, random, torch, time
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, "/home/stu001/vits_renge")
import commons, utils
from models import SynthesizerTrn
from text import text_to_sequence
from mel_processing import spec_to_mel_torch, spectrogram_torch

dev = torch.device('cuda')
cfg = json.load(open('/home/stu001/vits_finetune/configs/renge.json'))
hps = cfg
sym = hps['symbols']

print(f'Loading pretrained model...')
ckpt = torch.load('/home/stu001/vits_finetune/checkpoints/G_0.pth', map_location='cpu', weights_only=False)
st = ckpt['model']

model = SynthesizerTrn(len(sym), hps['data']['filter_length']//2+1,
    hps['train']['segment_size']//hps['data']['hop_length'],
    n_speakers=hps['data']['n_speakers'], **hps['model'])
model.load_state_dict(st, strict=False)
model = model.to(dev).train()
print(f'Model: {sum(p.numel() for p in model.parameters())/1e6:.1f}M')

MAX_TEXT_LEN = 60  # Filter texts too long for 0.37s segment (8192/256=32 frames)
class DS(torch.utils.data.Dataset):
    def __init__(self, fl):
        with open(fl, encoding="utf-8") as f:
            self.d = [(p[0], p[2]) if len(p:=l.strip().split("|", 2)) >= 3 else (p[0], p[1]) for l in f if l.strip() and "|" in l]
        print(f"Dataset: {len(self.d)} samples")
    def __len__(self): return len(self.d)
    def __getitem__(self, i):
        p, t = self.d[i][0], self.d[i][1]
        a, sr = utils.load_wav_to_torch(p); a = a / hps["data"]["max_wav_value"]  # normalize to [-1,1]
        SR = hps["data"]["sampling_rate"]
        if sr != SR:
            a = torch.from_numpy(__import__("librosa").resample(a.numpy(), orig_sr=sr, target_sr=SR)).float()
        seg = hps["train"]["segment_size"]
        if a.size(0) >= seg:
            start = torch.randint(0, a.size(0) - seg + 1, (1,)).item()
            a = a[start:start+seg]
        else:
            a = torch.nn.functional.pad(a, (0, seg - a.size(0)))
        seq = text_to_sequence(t, sym, hps["data"]["text_cleaners"])
        if hps["data"]["add_blank"]: seq = commons.intersperse(seq, 0)
        return torch.LongTensor(seq), a
def coll(batch):
    mx = max(len(x[0]) for x in batch)
    xp = torch.zeros(len(batch), mx, dtype=torch.long)
    for i, (t, _) in enumerate(batch): xp[i, :len(t)] = t
    return xp, torch.LongTensor([len(x[0]) for x in batch]), torch.stack([x[1] for x in batch]), torch.zeros(len(batch), dtype=torch.long)

ds = DS('/home/stu001/vits_finetune/filelists/renge_train.txt')
dl = DataLoader(ds, batch_size=2, shuffle=True, collate_fn=coll, drop_last=True)
print(f'Train: {len(ds)}, batches: {len(dl)}')

opt = torch.optim.AdamW(model.parameters(), lr=2e-4, betas=[0.8,0.99], eps=1e-9)
sch = torch.optim.lr_scheduler.ExponentialLR(opt, gamma=0.999875)
OUT = '/home/stu001/vits_finetune/output_gen'
os.makedirs(OUT, exist_ok=True)

FL, SR, HL, WL = hps['data']['filter_length'], hps['data']['sampling_rate'], hps['data']['hop_length'], hps['data']['win_length']
SEG = hps['train']['segment_size']
EPOCHS = 300

for ep in range(1, EPOCHS+1):
    total = 0
    pbar = tqdm(dl, desc=f'E{ep}')
    for x, xl, y, sid in pbar:
        x, xl, y, sid = x.to(dev), xl.to(dev), y.to(dev), sid.to(dev)
        y_spec = spectrogram_torch(y, FL, SR, HL, WL, center=False)
        y_hat, l_len, attn, ids, xm, ym, _ = model(x, xl, y_spec, torch.LongTensor([y_spec.size(2)]*y_spec.size(0)).to(dev), sid)
        mel = spec_to_mel_torch(y_spec, FL, 80, SR, 0.0, 8000.0)
        ymel = commons.slice_segments(mel, ids, SEG//HL)
        yh_spec = spectrogram_torch(y_hat.squeeze(1), FL, SR, HL, WL, center=False); yhm = spec_to_mel_torch(yh_spec, FL, 80, SR, 0.0, 8000.0)
        yhm = yhm[:, :, :ymel.shape[-1]]
        loss = nn.L1Loss()(yhm, ymel) * 45 + l_len.mean() * 0.1
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        total += loss.item(); pbar.set_postfix({'loss': f'{loss.item():.2f}'})
    sch.step()
    print(f'E{ep}: avg={total/len(dl):.4f}')
    if ep % 30 == 0:
        torch.save({'model': model.state_dict(), 'epoch': ep, 'hps': hps, 'symbols': sym}, os.path.join(OUT, f'ft_e{ep}.pth'))

torch.save({'model': model.state_dict(), 'epoch': EPOCHS, 'hps': hps, 'symbols': sym}, os.path.join(OUT, 'ft_final.pth'))
print('Done!')
