import numpy as np
import torch
from torch.nn.functional import binary_cross_entropy_with_logits
from torch.optim import Adam

from utils.torch_utils import to_float, torch_abs

def train_epoch(
    dag,
    train_dataloader,
    optimizer,
    loss=binary_cross_entropy_with_logits,
    atrition_regularization=0.025,
    atrition=0.0,
):

    epoch_loss = 0
    regularizer_loss = 0
    for batch_n, (xb, ytb) in enumerate(iter(train_dataloader), start=1):
        batch_value_loss, batch_reg_loss = train_batch(
            dag,
            xb,
            ytb,
            loss,
            optimizer,
            atrition_regularization=atrition_regularization,
            atrition=atrition,
        )
        epoch_loss += batch_value_loss + batch_reg_loss
        regularizer_loss += batch_reg_loss
    return epoch_loss / batch_n, regularizer_loss / batch_n

def train_batch(dag, x, yt, loss_fcn, optimizer, atrition_regularization=0.15, atrition=0.0):
    # Init
    optimizer.zero_grad()

    # Value loss
    yp = dag(x, training=True)
    value_loss = loss_fcn(yp, yt)

    # Regularization
    regularizer_loss = 0
    for n, node in enumerate(dag.nodes, 1):
        w = torch_abs(node.input_weights)
        b = torch_abs(node.bias)
        weight = 1 + (n / len(dag))
        regularizer_loss += atrition_regularization * atrition * ((w.sum() + b) / len(dag.nodes) ** 1) * weight

    # Add things up
    loss = value_loss + regularizer_loss
    loss.backward(retain_graph=True)
    optimizer.step()
    return value_loss, regularizer_loss

def compute_accuracy_and_atrition(dag, dataloader, old_accuracy):
    acc = 0
    for batch_n, (xb, ytb) in enumerate(iter(dataloader), start=1):
        ypb = dag(xb, training=False).round()
        acc += 1 - torch.abs((ypb - ytb)).mean()
    new_accuracy = acc / batch_n
    accuracy = to_float((1.0 - 0.05) * old_accuracy + 0.05 * new_accuracy)
    atrition = np.clip(2 * accuracy - 1, 0., 1.)
    return accuracy, atrition
