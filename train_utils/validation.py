
def initialize_trainer(epoch_count, snapshot_dir=None):
    import torch
    from models import get_model, get_optimizer_from_config, get_lr_scheduler_from_config
    from train_utils import RegressionTrainer
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    n = get_model()
    o = get_optimizer_from_config(n)
    s = get_lr_scheduler_from_config(o)
    t = RegressionTrainer(
        n, torch.nn.MSELoss(), o, s, epoch=epoch_count, snapshot_dir=snapshot_dir,
        verbose=False, progress=False, log_interval=1
    )
    t.to(device)
    return t


def out_of_fold_validation(num_epochs, random_state=777):

    import os
    import glob
    from sklearn.model_selection import train_test_split, KFold
    import torch
    from torch.utils.data import SubsetRandomSampler

    from data_prep_utils import get_processed_data, get_loader

    dataset = get_processed_data()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print("Validating by oof...\n")

    train_dataset, test_dataset = train_test_split(dataset, train_size=5, test_size=1, random_state=random_state)
    kf = KFold(n_splits=5, random_state=random_state, shuffle=True)

    predictions = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(train_dataset)):

        print("<Fold %s>\n" % fold)
        snapshot_dir = os.path.join('checkpoint', f'fold{fold}')
        fitter = initialize_trainer(num_epochs, snapshot_dir)
        _, test_result = fitter.fit(
            get_loader(train_dataset, sampler=SubsetRandomSampler(train_idx)),
            get_loader(train_dataset, sampler=SubsetRandomSampler(val_idx)),
            split_result=True
        )
        best_snapshot = sorted(glob.glob(os.path.join(snapshot_dir, 'best_checkpoint_epoch_*.pt')))[-1]
        fitter.load_state_dict(torch.load(best_snapshot))
        model = fitter.model

        with torch.no_grad():
            fold_prediction = []
            for x, _ in get_loader(test_dataset, train=False):
                fold_prediction.append(model(x.to(device)))
            fold_prediction = torch.cat(fold_prediction, dim=0).view(-1, 1)
            predictions.append(fold_prediction)

    with torch.no_grad():
        prediction_avg = sum(predictions) / len(predictions)
        ground_truth = []
        for _, y in get_loader(test_dataset, train=False):
            ground_truth.append(y.to(device))
        ground_truth = torch.cat(ground_truth, dim=0).view(-1, 1)

    return prediction_avg, ground_truth


def k_fold_early_stopping(num_folds, num_epochs, repeat):

    from sklearn.model_selection import KFold
    from torch.utils.data import SubsetRandomSampler

    from data_prep_utils import get_processed_data, get_loader

    dataset = get_processed_data()

    print("Calculating early stopping epoch from fold repeating...\n")

    early_stopping_epochs = []

    for i in range(1, repeat + 1):

        print("\n\n{Repeat %s}\n\n" % i)

        kf = KFold(n_splits=num_folds, random_state=i, shuffle=True)
        early_stopping = 0

        for fold, (train_idx, val_idx) in enumerate(kf.split(dataset)):

            print("<Fold %s>\n" % fold)

            train_loader = get_loader(dataset, sampler=SubsetRandomSampler(train_idx))
            val_loader = get_loader(dataset, sampler=SubsetRandomSampler(val_idx))

            fitter = initialize_trainer(num_epochs)
            _, test_result = fitter.fit(train_loader, val_loader, split_result=True)
            early_stopping += test_result.index(min(test_result)) + 1

        print()

        early_stopping /= num_folds
        early_stopping_epochs.append(early_stopping)

    return early_stopping_epochs