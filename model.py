import torch
import torch.nn as nn
from torch.hub import load_state_dict_from_url
from torch.autograd import Function

from copy import deepcopy


__all__ = ['AlexNet', 'alexnet']


model_urls = {
    'alexnet': 'https://download.pytorch.org/models/alexnet-owt-4df8aa71.pth',
}

class ReverseLayerF(Function):
    # Forwards identity
    # Sends backward reversed gradients
    @staticmethod
    def forward(ctx, x, alpha):
        ctx.alpha = alpha

        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        output = grad_output.neg() * ctx.alpha

        return output, None
    


class AlexNetDANN(nn.Module):

    def __init__(self, num_classes=1000):
        super(AlexNetDANN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.classifier = nn.Sequential(
            nn.Dropout(),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Linear(4096, num_classes),
        )
        
        self.domainClassifier = nn.Sequential()

    def forward(self, x, alpha=None):
        features = self.features(x)
        features = self.avgpool(features)
        # Flatten the features:
        features = torch.flatten(features, 1)
        # If we pass alpha, we can assume we are training the discriminator
        if alpha is not None:
            # gradient reversal layer (backward gradients will be reversed)
            reverse_feature = ReverseLayerF.apply(features, alpha)
            discriminator_output = self.domainClassifier(reverse_feature)
            return discriminator_output
        # If we don't pass alpha, we assume we are training with supervision
        else:
            # do something else
            class_outputs = self.classifier(features)
            return class_outputs


    def alexnet_dann(pretrained=False, progress=True):
        model = AlexNetDANN()
        if pretrained:
            state_dict = load_state_dict_from_url(model_urls['alexnet'],
                                              progress=progress)
            model.load_state_dict(state_dict)
        
        model.domainClassifier = deepcopy(model.classifier)
    
        model.classifier[6] = nn.Linear(4096, 7)
        model.domainClassifier[6] = nn.Linear(4096, 2)
    
        return model
