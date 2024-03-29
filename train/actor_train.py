import torch
import torch.nn as nn
import torchvision
import numpy as np
import argparse
from TD3 import TD3
from utils import create_directory, plot_learning_curve, scale_action
import random
import os
from multiprocessing import Process
import time

def script(epoch, id, train_time, all_rl_abstraction):
    os.system("./../src/build/CFR "+str(epoch)+" "+str(id)+" "+str(train_time)+" "+str(all_rl_abstraction))

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
parser = argparse.ArgumentParser()
parser.add_argument('--ckpt_dir', type=str, default='../action_checkpoint/')
parser.add_argument('--figure_file', type=str, default='../action_checkpoint/reward.png')
parser.add_argument('--actor_figure_file', type=str, default='../action_checkpoint/actorloss.png')
parser.add_argument('--critic_figure_file', type=str, default='../action_checkpoint/criticloss.png')
parser.add_argument('--action_noise',type=float, default=0.15)
parser.add_argument('--threads',type=int, default=60)
parser.add_argument('--learn_time',type=int,default=15000)
parser.add_argument('--action_dim',type=int,default=10)
parser.add_argument('--state_dim',type=int,default=32)
parser.add_argument('--epoch',type=int,default=200)
args = parser.parse_args()
agent = TD3(lr_actor=0.0003, lr_critic=0.0003, state_dim=args.state_dim,
            action_dim=args.action_dim, actor_fc1_dim=128, actor_fc2_dim=96,
            critic_fc1_dim=128, critic_fc2_dim=96, learn_time=args.learn_time, ckpt_dir=args.ckpt_dir, gamma=0.99,
            tau=0.005, action_noise=0.15, policy_noise=0.2, policy_noise_clip=0.5,
            delay_time=2, max_size=1000000, batch_size=1024)


actor_loss_history = []
critic_loss_history = []
avg_reward_history = []

def main():

    for epoch in range(args.epoch):
        print('epoch:',epoch)
        start = time.time()
        model = agent.target_actor.to(device)
        model.eval()
        example=torch.rand(1,args.state_dim).to(device)
        traced_script_module = torch.jit.trace(model, example)
        traced_script_module.save("../model/actor.pt")

        model = agent.target_critic1.to(device)
        model.eval()
        example2 = torch.rand(1,args.state_dim+args.action_dim).to(device)
        traced_script_module2 = torch.jit.trace(model, example2)
        torch.jit.save(traced_script_module2,"../model/critic.pt")

        threads = []
        rl_abstraction = 0
        if epoch > 20:
            rl_abstraction = 1
        for i in range(args.threads):
            threads.append(Process(target=script, args=(epoch,i,args.data_train_time,rl_abstraction,)))
            threads[i].start()

        for i in range(args.threads):
            threads[i].join()
        
        average_value = 0.0
        for i in range(args.threads):
            state = np.loadtxt("../data/rlstate{}_{}.csv".format(epoch,i)).reshape(-1,args.state_dim)
            action = np.loadtxt("../data/rlaction{}_{}.csv".format(epoch,i)).reshape(-1,args.action_dim)
            value = np.loadtxt("../data/rlvalue{}_{}.csv".format(epoch,i)).reshape(-1,1)
            average_value += value.mean()
            for j in range(state.shape[0]):
                agent.remember(state[j],action[j],value[j])
        end = time.time()
        print('data time:',end-start,'s')
        actor_loss, critic_loss = agent.learn()
        agent.save_models(epoch)
        avg_reward_history.append(average_value)
        actor_loss_history.append(actor_loss)
        critic_loss_history.append(critic_loss)
        end = time.time()
        print('average reward:',average_value)
    
    episodes = [i+1 for i in range(args.epoch)]
    plot_learning_curve(episodes, avg_reward_history, title='AvgReward', ylabel='reward', figure_file=args.figure_file)
    episodes = [i+1 for i in range(args.epoch)]
    plot_learning_curve(episodes, actor_loss_history, title='ActorLoss', ylabel='loss', figure_file=args.actor_figure_file)
    episodes = [i+1 for i in range(args.epoch)]
    plot_learning_curve(episodes, critic_loss_history, title='CriticLoss', ylabel='loss', figure_file=args.critic_figure_file)
    
    
    
if __name__ == '__main__':
    main()
