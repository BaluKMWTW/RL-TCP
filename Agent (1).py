#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import gym
import tensorflow as tf
import tensorflow.contrib.slim as slim
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from tensorflow import keras
from ns3gym import ns3env


import argparse
from ns3gym import ns3env
from tcp_base import TcpTimeBased
from tcp_newreno import TcpNewReno

parser = argparse.ArgumentParser(description='Start simulation script on/off')
parser.add_argument('--start',
                    type=int,
                    default=1,
                    help='Start ns-3 simulation script 0/1, Default: 1')
parser.add_argument('--iterations',
                    type=int,
                    default=1,
                    help='Number of iterations, Default: 1')
args = parser.parse_args()
startSim = bool(args.start)
iterationNum = int(args.iterations)

port_num = 5555
sim_time = 10
step = 0.5
seed = 12
simArgs = {"--duration": sim_time,}
debug = False

env = ns3env.Ns3Env(port_num=port_num, step=step, startSim=startSim, simSeed=seed, simArgs=simArgs, debug=debug)
env.reset()

ob_space = env.observation_space
ac_space = env.action_space

print("Observation space: ", ob_space,  ob_space.dtype)
print("Action space: ", ac_space, ac_space.dtype)


def get_agent(obs):
    socketUuid = obs[0]
    tcpEnvType = obs[1]
    tcpAgent = get_agent.tcpAgents.get(socketUuid, None)
    if tcpAgent is None:
        if tcpEnvType == 0:
            # event-based = 0
            tcpAgent = TcpNewReno()
        else:
            # time-based = 1
            tcpAgent = TcpTimeBased()
        tcpAgent.set_spaces(get_agent.ob_space, get_agent.ac_space)
        get_agent.tcpAgents[socketUuid] = tcpAgent

    return tcpAgent

# initialize variable
get_agent.tcpAgents = {}
get_agent.ob_space = ob_space
get_agent.ac_space = ac_space

s_size = ob_space.shape[0]
print("State size: ",ob_space.shape[0])

a_size = 3
print("Action size: ", a_size)

model = keras.Sequential()
model.add(keras.layers.Dense(s_size, input_shape=(s_size,), activation='relu'))
model.add(keras.layers.Dense(s_size, input_shape=(s_size,), activation='relu'))
model.add(keras.layers.Dense(a_size, activation='softmax'))
model.compile(optimizer=tf.train.AdamOptimizer(0.0012),
              loss='categorical_crossentropy',
              metrics=['accuracy'])

total_episodes = 6
max_env_steps = 100
env._max_episode_steps = max_env_steps

epsilon = 1.0               # exploration rate
epsilon_min = 0.01
epsilon_decay = 0.993

time_history = []
reward_history = []
cWnd_history=[]
cWnd_history2=[]
Rtt=[]
segAkc=[]
No_step = 0
t2 =10
t =[]
reward = 0
done = False
info = None
# action mapping 
a_mapping = {}
a_mapping[0] = 0
a_mapping[1] = 600
a_mapping[2] = -60
U_new =0
U =0
U_old=0
reward=0
for e in range(total_episodes):
    obs = env.reset()
    cWnd = obs[5]
    obs = np.reshape(obs, [1, s_size])
    rewardsum = 0
    for time in range(max_env_steps):
        # Choose action
        if np.random.rand(1) < epsilon:
            action_index = np.random.randint(3)
            print (action_index)
            print("Value Initialization ...")
        else:
            action_index = np.argmax(model.predict(obs)[0])
            print(action_index)
        new_cWnd = cWnd + a_mapping[action_index]
        new_ssThresh = np.int(cWnd/2)
        actions = [new_ssThresh, new_cWnd]
        U_new=0.7*(np.log(obs[0,2]))-0.7*(np.log(obs[0,9]))
        U=U_new-U_old
        if U <-0.05:
            reward=-5
        elif U >0.05:
            reward=1
        else:
            reward=0
        # Step
        next_state, reward, done, info = env.step(actions)
        cWnd = next_state[5]
        print("cWnd:",cWnd)
        if done:
            print("episode: {}/{}, time: {}, rew: {}, eps: {:.2}"
                  .format(e, total_episodes, time, rewardsum, epsilon))
            break
        U_old=0.7*(np.log(obs[0,2]))-0.7*(np.log(obs[0,9]))
        next_state = np.reshape(next_state, [1, s_size])
        # Train
        target = reward
        if not done:
            target = (reward + 0.95 * np.amax(model.predict(next_state)[0]))
        target_f = model.predict(obs)
        print("target :", target_f)
        target_f[0][action_index] = target
        model.fit(obs, target_f, epochs=1, verbose=0)

        obs = next_state
        seg=obs[0,5]
        rtt=obs[0,9]
        rewardsum += reward
        if epsilon > epsilon_min: epsilon *= epsilon_decay
        No_step += 1
  
        print("number of steps :", No_step)
        print("espsilon :",epsilon)

  
        print("reward sum", rewardsum)
        segAkc.append(seg)
        Rtt.append(rtt)

        cWnd_history.append(cWnd)
        time_history.append(time)
        reward_history.append(rewardsum)


        
    print("Plot Learning Performance")
    mpl.rcdefaults()
    mpl.rcParams.update({'font.size': 16})
    fig, ax = plt.subplots(figsize=(10,4))
    plt.grid(True, linestyle='--')
    plt.title('Learning Performance')
    #plt.plot(range(len(rew_history)), rew_history, label='Reward', marker="^", linestyle=":")#, color='red')
    plt.plot(range(len(reward_history)), reward_history, label='Reward', marker="", linestyle="-")#, color='k')

    #plt.plot(range(len(segAkc)), segAkc, label='segAkc', marker="", linestyle="-"),# color='b')
    #plt.plot(range(len(Rtt)),Rtt, label='Rtt', marker="", linestyle="-")#, color='y')
    plt.xlabel('Episode')
    plt.ylabel('Steps')
    plt.legend(prop={'size': 12})
    plt.savefig('learning.pdf', bbox_inches='tight')
    plt.show() 


