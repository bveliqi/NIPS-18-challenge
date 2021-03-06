import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.datasets as datasets
import torch.utils.data as data

import torchvision.transforms as transforms

from torch.autograd import Variable

import math
import os


model_url = 'https://download.pytorch.org/models/resnet50-19c8e357.pth'

# --- HELPERS ---

def conv3x3(in_planes, out_planes, stride=1):
    '''
        3x3 convolution with padding
    '''
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


# --- COMPONENTS ---

class BasicBlock(nn.Module):
    
    expansion = 1
    
    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride
        
    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out



class Bottleneck(nn.Module):
    
    expansion = 4
    
    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride
    
    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        # print(f"out: {out.size()} - residual: {residual.size()}")
        out += residual
        out = self.relu(out)

        return out


# --- ResNet-50 ---

class ResNet(nn.Module):
    
    def __init__(self, block, layers, num_classes=1000):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,  bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(2, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        # print(f"avgpool: {self.avgpool} - c: {x.size()}")
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


# --- MAIN ---

if __name__ == "__main__":
    net = ResNet(Bottleneck, [3, 4, 6, 3])

    cuda = False if os.getenv('CUDA') == 'False' else True
    print(f"Using CUDA: {cuda}")

    if cuda:
        net.cuda()
    else:
        cuda

    # loss function + optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9)

    # load data set
    print(f"Reading data...")
    train_dir = 'data/tiny-imagenet-200/train'
    val_dir = 'data/tiny-imagenet-200/val'
    train_dataset = datasets.ImageFolder(train_dir, transform=transforms.ToTensor())
    val_dataset = datasets.ImageFolder(val_dir, transform=transforms.ToTensor())
    train_loader = data.DataLoader(train_dataset, batch_size=32)
    print(f"Loaded: {train_dir}")
    val_loader = data.DataLoader(val_dataset, batch_size=32)
    print(f"Loaded: {val_dir}")

    '''
    train_dataset = torchvision.datasets.CIFAR100(root='./data', train=True, download=True, transform=transforms.ToTensor())
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=4, shuffle=True, num_workers=2)
    '''


    # train the model
    learning_rate = 0.01
    for epoch in range(100):
        print(f"-- EPOCH: {epoch}")
        running_loss = 0.0
        for i, data in enumerate(train_loader, 0):
            print(f"-- ITERATION: {i}")
            input, target = data

            # wrap input + target into variables
            input_var = Variable(input).cuda() if cuda else Variable(input)
            target_var = Variable(target).cuda() if cuda else Variable(target)

            # compute output
            output = net(input_var)
            loss = criterion(output, target_var)

            # computer gradient + sgd step
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # print progress
            running_loss += loss.data[0]
            if i % 2000 == 1999:  # print every 2k mini-batches
                print(f"-- RUNNING_LOSS: {running_loss / 2000}")
                running_loss = 0.0

    print('Finished Training')
    torch.save(net.state_dict(), "/models/baseline-resnet50.pt")