import sys, torch, json
sys.path.insert(0, 'vits_infer')
import commons; from models import SynthesizerTrn
from text import text_to_sequence
import soundfile as sf

ckpt = torch.load('moe_tts_models/slot4/sayashi_ft.pth', map_location='cpu', weights_only=False)
st = ckpt['model']

# Exact symbols from training
syms = ['_', ',', '.', '!', '?', '-', '~', '…', 'A', 'E', 'I', 'N', 'O', 'Q', 'U',
 'a', 'b', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's',
 't', 'u', 'v', 'w', 'y', 'z', 'ʃ', 'ʧ', 'ʦ', 'ɯ', 'ɹ',
 'ə', 'ɥ', '⁼', 'ʰ', '`', '→', '↓', '↑', ' ']

m = SynthesizerTrn(len(syms), 513, 32, n_speakers=804,
    inter_channels=192, hidden_channels=192, filter_channels=768,
    n_heads=2, n_layers=6, kernel_size=3, p_dropout=0.1, resblock='1',
    resblock_kernel_sizes=[3,7,11], resblock_dilation_sizes=[[1,3,5],[1,3,5],[1,3,5]],
    upsample_rates=[8,8,2,2], upsample_initial_channel=512, upsample_kernel_sizes=[16,16,4,4],
    n_layers_q=3, use_spectral_norm=False, gin_channels=256)
miss, unexp = m.load_state_dict(st, strict=False)
print(f'Missing: {len(miss)}, Unexpected: {len(unexp)}')
m = m.cuda().eval()

for i, t in enumerate(['こんにちは', 'おやすみなさい']):
    seq = text_to_sequence(t, syms, ['japanese_cleaners'])
    seq = commons.intersperse(seq, 0)
    x = torch.LongTensor(seq).unsqueeze(0).cuda()
    with torch.no_grad():
        a = m.infer(x, torch.LongTensor([len(seq)]).cuda(), sid=torch.LongTensor([0]).cuda(),
            noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0)[0][0,0].cpu().numpy()
    sf.write(f'test_sayashi_{i+1}.wav', a, 22050)
    print(f'test_sayashi_{i+1}.wav: {len(a)/22050:.1f}s, max={a.max():.3f}, min={a.min():.3f}')
