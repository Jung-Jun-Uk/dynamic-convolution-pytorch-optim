import os
import sys
import errno
import glob
import re
from pathlib import Path

import torch
import torch.backends.cudnn as cudnn

        
def init_torch_seeds(seed=0):
    # Speed-reproducibility tradeoff https://pytorch.org/docs/stable/notes/randomness.html
    torch.manual_seed(seed)
    if seed == 0:  # slower, more reproducible
        cudnn.deterministic = True
        cudnn.benchmark = False
    else:  # faster, less reproducible
        cudnn.deterministic = False
        cudnn.benchmark = True

    
def print_argument_options(opt):
    conf = vars(opt)
    print("Config FILE")
    for key, value in conf.items():
        print('{:<25} = {}'.format(key,value))
    print("\n\n")


def mkdir_if_missing(directory):
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

class AverageMeter(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0
    
    def update(self, val, n=1):
        self.val = val
        self.sum += val*n
        self.count += n
        self.avg = self.sum / self.count

class Logger(object):
    def __init__(self, fpath=None):
        self.console = sys.stdout
        self.file = None
        if fpath is not None:
            mkdir_if_missing(os.path.dirname(fpath))
            self.file = open(fpath, 'w')
            
    def __del__(self):
        self.close()
    
    def __exit__(self, *args):
        self.close()
    
    def write(self, msg):
        self.console.write(msg)
        if self.file is not None:
            self.file.write(msg)
    
    def flush(self):
        self.console.flush()
        if self.file is not None:
            self.file.flush()
            os.fsync(self.file.fileno())
            
    def close(self):
        self.console.close()
        if self.file is not None:
            self.file.close()


def increment_path(path, exist_ok=True, sep=''):
    # Increment path, i.e. runs/exp --> runs/exp{sep}0, runs/exp{sep}1 etc.
    path = Path(path)
    if (path.exists() and exist_ok) or (not path.exists()):
        return str(path)
    else:
        dirs = glob.glob(f"{path}{sep}*")  # similar paths
        matches = [re.search(rf"%s{sep}(\d+)" % path.stem, d) for d in dirs]
        i = [int(m.groups()[0]) for m in matches if m]  # indices
        n = max(i) + 1 if i else 2  # increment number
        return f"{path}{sep}{n}"  # update path

def select_device(device='', batch_size=None):
    # device = 'cpu' or '0' or '0,1,2,3', rank = print only once during distributed parallel
    cpu_request = device.lower() == 'cpu'
    if device and not cpu_request:  # if device requested other than 'cpu'
        os.environ['CUDA_VISIBLE_DEVICES'] = device  # set environment variable
        assert torch.cuda.is_available(), 'CUDA unavailable, invalid device {} requested'.format(device)  # check availablity
        
    cuda = False if cpu_request else torch.cuda.is_available()
    if cuda:
        c = 1024 ** 2  # bytes to MB
        ng = torch.cuda.device_count()
        if ng > 1 and batch_size:  # check that batch_size is compatible with device_count
            assert batch_size % ng == 0, 'batch-size {} not multiple of GPU count {}'.format(batch_size, ng)
        x = [torch.cuda.get_device_properties(i) for i in range(ng)]
        s = f'Using torch {torch.__version__} '
        
        for i in range(0, ng):
            if i == 1:
                s = ' ' * len(s)
            print("{}CUDA:{} ({}, {}MB)".format(s, i, x[i].name, x[i].total_memory / c))
    else:
        print(f'Using torch {torch.__version__} CPU')

    print('')  # skip a line
    return torch.device('cuda:0' if cuda else 'cpu') 


def save_model(model, epoch, name, save_dir):
    dirname = os.path.join(save_dir, 'weights')
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    save_name = os.path.join(dirname, name + '_epoch_' + str(epoch+1) + '.pth')
    torch.save(model.state_dict(), save_name)    