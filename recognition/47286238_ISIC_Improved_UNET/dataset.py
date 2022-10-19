import torch, torchvision
from torchvision import transforms as T
import pandas
import os

class Dataset(torch.utils.data.Dataset):
    def __init__(self, data_path, truth_path, metadata_path) -> None:
        self.data_path = data_path
        self.truth_path = truth_path
        self.metadata = pandas.read_csv(metadata_path)

    def __len__(self):
        """
        Reports the size of the dataset
        Required in order to use DataLoader
        """
        len_data = len([file for file in os.listdir(self.data_path)])
        return len_data

    def __getitem__(self, key):
        """ 
        Yields a data-groundtruth sample for a given key
        """
        resize = T.Resize((256,256))

        data_id = self.metadata.iloc[key]['image_id']
        data_path = os.path.join(self.data_path, data_id + '.jpg')
        data = torchvision.io.read_image(data_path, mode=torchvision.io.ImageReadMode.RGB)
        # resize and normalize to values between 0 and 1
        data = resize(data)
        data = torch.divide(data, 255)

        truth_path = os.path.join(self.truth_path, data_id + '_segmentation.png')
        truth = torchvision.io.read_image(truth_path, mode=torchvision.io.ImageReadMode.RGB)
        truth = resize(truth)
        truth = torch.divide(truth, 255)

        return data, truth

dataset_train = Dataset(
        data_path='data/training/data', 
        truth_path='data/training/truth', 
        metadata_path='data/training/data/ISIC-2017_Training_Data_metadata.csv'
        )
data, truth = dataset_train[0]
print(data.max())
print(data.min())
print(data.shape)
print(truth.max())
print(truth.min())
print(truth.shape)
print(len(dataset_train))

