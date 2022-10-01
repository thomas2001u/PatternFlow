from torch import nn
import torch
import math
import torch.nn.functional as F
import matplotlib.pyplot as plt
from torchvision import transforms
import numpy as np
import matplotlib.image as mpimg
import os
import glob
from torch.utils.tensorboard import SummaryWriter

def show_tensor_image(image):
    """
    Helper function to display images from tensors
    """
    reverse_transforms = transforms.Compose([
        transforms.Lambda(lambda t: (t + 1) / 2),
        transforms.Lambda(lambda t: t.permute(1, 2, 0)), # CHW to HWC
        transforms.Lambda(lambda t: t * 255.),
        transforms.Lambda(lambda t: t.numpy().astype(np.uint8)),
        transforms.ToPILImage(),
    ])

    # Take first image of batch
    if len(image.shape) == 4:
        image = image[0, :, :, :] 
    plt.imshow(reverse_transforms(image))

"""
----------
Networks
-----------
"""

class Block(nn.Module):
    """
    Single unet block
    """
    def __init__(self, in_ch, out_ch, time_emb_dim, up=False):
        super().__init__()
        self.time_mlp =  nn.Linear(time_emb_dim, out_ch)
        if up:
            self.conv1 = nn.Conv2d(2*in_ch, out_ch, 3, padding=1)
            self.transform = nn.ConvTranspose2d(out_ch, out_ch, 4, 2, 1)
        else:
            self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
            self.transform = nn.Conv2d(out_ch, out_ch, 4, 2, 1)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.bnorm1 = nn.BatchNorm2d(out_ch)
        self.bnorm2 = nn.BatchNorm2d(out_ch)
        self.relu  = nn.ReLU()
        
    def forward(self, x, t, ):
        # First Conv
        h = self.bnorm1(self.relu(self.conv1(x)))
        # Time embedding
        time_emb = self.relu(self.time_mlp(t))
        # Extend last 2 dimensions
        time_emb = time_emb[(..., ) + (None, ) * 2]
        # Add time channel
        h = h + time_emb
        # Second Conv
        h = self.bnorm2(self.relu(self.conv2(h)))
        # Down or Upsample
        return self.transform(h)

class SinusoidalPositionEmbeddings(nn.Module):
    """
    Embeds timestep position
    """
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, time):
        device = time.device
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = time[:, None] * embeddings[None, :]
        embeddings = torch.cat((embeddings.sin(), embeddings.cos()), dim=-1)
        return embeddings

class Unet(nn.Module):
    """
    Simple Unet
    """
    def __init__(self):
        super().__init__()
        image_channels = 3
        down_channels = (64, 128, 256, 512, 1024)
        up_channels = (1024, 512, 256, 128, 64)
        out_dim = 1 
        time_emb_dim = 32

        # Time embedding
        self.time_mlp = nn.Sequential(
                SinusoidalPositionEmbeddings(time_emb_dim),
                nn.Linear(time_emb_dim, time_emb_dim),
                nn.ReLU()
            )
        
        # Initial projection
        self.conv0 = nn.Conv2d(image_channels, down_channels[0], 3, padding=1)

        # Downsample
        self.downs = nn.ModuleList([Block(down_channels[i], down_channels[i+1], \
                                    time_emb_dim) \
                    for i in range(len(down_channels)-1)])
        # Upsample
        self.ups = nn.ModuleList([Block(up_channels[i], up_channels[i+1], \
                                        time_emb_dim, up=True) \
                    for i in range(len(up_channels)-1)])

        self.output = nn.Conv2d(up_channels[-1], 3, out_dim)

    def forward(self, x, timestep):
        # Embedd time
        t = self.time_mlp(timestep)
        # Initial conv
        x = self.conv0(x)
        # Unet
        residual_inputs = []
        for down in self.downs:
            x = down(x, t)
            residual_inputs.append(x)
        for up in self.ups:
            residual_x = residual_inputs.pop()
            # Add residual x as additional channels
            x = torch.cat((x, residual_x), dim=1)           
            x = up(x, t)
        return self.output(x)

"""
------------
Training
------------
"""

class Trainer:
    """
    Class to train Unet Diffusion model
    """
    def __init__(self, model, img_size, timesteps=300, start=0.0001, end=0.02):
        self.img_size = img_size
        self.T = timesteps
        self.start = start
        self.end = end
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("Using Device: ", self.device)

        #Precalculate normal distribution values
        self.betas = self.linear_beta_schedule()
        self.alphas = 1. - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, axis=0)
        self.alphas_cumprod_prev = F.pad(self.alphas_cumprod[:-1], (1, 0), value=1.0)
        self.sqrt_recip_alphas = torch.sqrt(1.0 / self.alphas)
        self.sqrt_alphas_cumprod = torch.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1. - self.alphas_cumprod)
        self.posterior_variance = self.betas * (1. - self.alphas_cumprod_prev) / (1. - self.alphas_cumprod)

        #Attach model to device
        self.model = model.to(self.device)

    def linear_beta_schedule(self):
        """
        Diffusion noise schedule
        """
        return torch.linspace(self.start, self.end, self.T)
    
    def loss_fn(self, noise, noise_pred):
        """
        Loss function
        """
        return F.l1_loss(noise, noise_pred)

    def get_index_from_list(self, vals, t, x_shape):
        """ 
        Returns a specific index t of a passed list of values vals
        while considering the batch dimension.
        """
        batch_size = t.shape[0]
        out = vals.gather(-1, t.cpu())
        return out.reshape(batch_size, *((1,) * (len(x_shape) - 1))).to(t.device)

    def sample_forward(self, x_0, t):
        """
        Performs forward step adding noise to image.

        Takes noiseless image x_0 and adds equavalent noise to timestep t
        """
        noise = torch.randn_like(x_0)
        sqrt_alphas_cumprod_t = self.get_index_from_list(self.sqrt_alphas_cumprod, t, x_0.shape)
        sqrt_one_minus_alphas_cumprod_t = self.get_index_from_list(
            self.sqrt_one_minus_alphas_cumprod, t, x_0.shape
        )

        # mean + variance
        return sqrt_alphas_cumprod_t.to(self.device) * x_0.to(self.device) + sqrt_one_minus_alphas_cumprod_t.to(self.device) * noise.to(self.device), noise.to(self.device)

    @torch.no_grad()
    def sample_reverse(self, x, t):
        """
        Performs reverse step taking noisy image and calls model to denoise.
        """
        betas_t = self.get_index_from_list(self.betas, t, x.shape)
        sqrt_one_minus_alphas_cumprod_t = self.get_index_from_list(
            self.sqrt_one_minus_alphas_cumprod, t, x.shape
        )
        sqrt_recip_alphas_t = self.get_index_from_list(self.sqrt_recip_alphas, t, x.shape)
        
        # Call model (current image - noise prediction)
        model_mean = sqrt_recip_alphas_t * (
            x - betas_t * self.model(x, t) / sqrt_one_minus_alphas_cumprod_t
        )
        posterior_variance_t = self.get_index_from_list(self.posterior_variance, t, x.shape)
        
        if t == 0:
            return model_mean
        else:
            noise = torch.randn_like(x)
            return model_mean + torch.sqrt(posterior_variance_t) * noise

    def predict(self, x_0, t):
        """
        Creates an image with noise of timestep t and calls model to predict noise.

        Returns loss between actual noise and predicted noise.
        """
        x_noisy, noise = self.sample_forward(x_0, t)
        noise_pred = self.model(x_noisy, t)
        return self.loss_fn(noise, noise_pred)
    
    @torch.no_grad()
    def generate_image_plot(self, path, num_images=10):
        """
        Performs backward denoising to noise to generate new image.
        Plots num_images over all timesteps
        """
        img = torch.randn((1, 3, self.img_size, self.img_size), device=self.device)
        plt.figure(figsize=(15,15))
        plt.axis('off')
        stepsize = int(self.T/num_images)

        for i in range(0, self.T)[::-1]:
            t = torch.full((1,), i, device=self.device, dtype=torch.long)
            img = self.sample_reverse(img, t)
            if i % stepsize == 0:
                plt.subplot(1, num_images, int(i/stepsize+1))
                show_tensor_image(img.detach().cpu())
        plt.savefig(path, bbox_inches='tight')
        plt.close()

    @torch.no_grad()
    def generate_image(self, path):
        """
        Generates new image by completing full reverse denoising of all timesteps.

        Saves image to path.
        """
        img = torch.randn((1, 3, self.img_size, self.img_size), device=self.device)

        for i in range(0, self.T)[::-1]:
            t = torch.full((1,), i, device=self.device, dtype=torch.long)
            img = self.sample_reverse(img, t)
        
        mpimg.imsave(path, np.clip((img.detach().cpu().numpy()[0].T + 1) * 0.5, 0.0, 1.0))
    
    def fit(self, dataloader, epochs, optimizer):
        """
        Trains model for epochs using dataloader and optimizer 
        """
        #Create or empty output folders
        exists = os.path.exists('outputs')
        if not exists:
            os.makedirs('outputs')
        else:
            files = glob.glob("outputs/*")
            for f in files:
                os.remove(f)

        exists = os.path.exists('plots')
        if not exists:
            os.makedirs('plots')
        else:
            files = glob.glob("plots/*")
            for f in files:
                os.remove(f)

        #Create tensorboard run
        sw = SummaryWriter("runs")

        #detect batch size
        batch_size = dataloader.batch_size

        #Train
        for epoch in range(epochs):
            for step, batch in enumerate(dataloader):
                optimizer.zero_grad()
                #create random timestep in possible timesteps
                t = torch.randint(0, self.T, (batch_size,), device=self.device).long()

                loss = self.predict(batch, t)
                loss.backward()
                optimizer.step()

                if step == 0:
                    print(f"Epoch {epoch} Loss: {loss.item()}")
                    self.generate_image_plot(f"plots/plot_epoch{epoch}.jpeg")
                    self.generate_image(f"outputs/diff_epoch{epoch}.jpeg")
                    #tensorboard
                    sw.add_scalar("Loss", loss, epoch)
                    self.save_model('autosave.pth')
            print("Done!")

    def save_model(self, path):
        """
        Save model to path
        """
        torch.save(self.model, path)

    def load_model(self, path):
        """
        Load model
        """
        if 'model' in locals():
            self.model.cpu()
            torch.cuda.empty_cache()
        
        self.model = torch.load(path, map_location='cpu')
        self.model.to(self.device)