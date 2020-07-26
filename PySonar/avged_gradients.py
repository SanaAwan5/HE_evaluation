import warnings
import numpy as np
import phe as paillier
import time
from sonar.contracts_listclass import ModelRepository,Model,Gradient_List
from syft.he.paillier.keys import KeyPair,SecretKey,PublicKey
from syft.nn.linear import LinearClassifier
from sklearn.datasets import load_breast_cancer
#from itertools import cycle

start = time.time()
def get_balance(account):
    return repo.web3.fromWei(repo.web3.eth.getBalance(account),'ether')

warnings.filterwarnings('ignore')

# for the purpose of the simulation, we're going to split our dataset up amongst
# the relevant simulated users

cancer = load_breast_cancer()
y = cancer.target
X = cancer.data

validation = (X[46:51],y[46:51])
anonymous_users = (X[52:],y[52:])

# we're also going to initialize the model trainer smart contract, which in the
# real world would already be on the blockchain (managing other contracts) before
# the simulation begins

# ATTENTION: copy paste the correct address (NOT THE DEFAULT SEEN HERE) from truffle migrate output.
repo = ModelRepository('0xEc40aA837dB3cf71DFa2a153A151d0425439900A') # blockchain hosted model repository

# we're going to set aside 10 accounts for our 42 patients
# Let's go ahead and pair each data point with each patient's 
# address so that we know we don't get them confused
patient_addresses = repo.web3.eth.accounts[2:11]
anonymous_patients = list(zip(patient_addresses,
                               anonymous_users[0],
                               anonymous_users[1]))

# we're going to set aside 1 account for Cure Cancer Inc
cure_cancer_inc = repo.web3.eth.accounts[0]
agg_addr = repo.web3.eth.accounts[1]

pubkey,prikey = KeyPair().generate(n_length=2048)
#pubkey,prikey=paillier.paillier.generate_paillier_keypair()
cancer_classifier = LinearClassifier(desc="CancerClassifier",n_inputs=30,n_labels=1)
initial_error = cancer_classifier.evaluate(validation[0],validation[1])
start_modelencryption=time.time()
cancer_classifier.encrypt(pubkey)
end_modelencryption=time.time()
print('modelencryption time', end_modelencryption - start_modelencryption)
start_prikeyshare_gen = time.time()
s1,s2=paillier.paillier.genKeyShares(prikey.sk,pubkey.pk)
st=SecretKey(s1)
sab=SecretKey(s2)
s3,s4=paillier.paillier.genKeyShares(s2,pubkey.pk)
sa=SecretKey(s3)
scb=SecretKey(s4)
end_prikeyshare_gen=time.time()
print('keygentime',end_prikeyshare_gen - start_prikeyshare_gen)

disease_model = Model(owner=cure_cancer_inc,
                       syft_obj = cancer_classifier,
                       bounty = 2,
                       initial_error = initial_error,
                       target_error = 100,
                       best_error= initial_error
                      )
start_wmodel=time.time()
model_id = repo.submit_model(disease_model)
end_wmodel = time.time()
print('model write time to chain',end_wmodel - start_wmodel)
print('initial error',initial_error)
model=repo[model_id]
patient_address,input_data,target_data = anonymous_patients[0]
#gradient=model.generate_gradient(diabetic_address,input_data,target_data)
#start_wtrgrad=time.time()
#model.submit_transformed_gradients(gradient,st)
#end_wtrgrad=time.time()
#print('gradient write time to chain',end_wtrgrad - start_wtrgrad)

#old_balance = get_balance(diabetic_address)
#print(old_balance)
#gradient_list=Gradient_List(model_id, repo=repo, model=model)
#gradient_list[model_id]
model=repo[model_id]
#avg_gradient=gradient_list.generate_gradient_avg(agg_addr,sa,alpha=2)
#new_error,updatedModel = model.evaluate_gradient_from_avg(cure_diabetes_inc,agg_addr,avg_gradient,scb,prikey,pubkey,validation[0],validation[1])
#print('new_error',new_error)
#new_balance = get_balance(diabetic_address)
#incentive = new_balance - old_balance
#print(incentive)
print(repo[model_id])
end = time.time()
exec1=end - start
start2=time.time()
print("exec time1", exec1)
for i,(addr, input, target) in enumerate(anonymous_patients):
    model = repo[model_id]
    #print('model_id',model_id)
# patient is doing this
    gradient=model.generate_gradient(addr,input,target)
    start_wtrgrad=time.time()
    model.submit_transformed_gradients(gradient,st)
    end_wtrgrad=time.time()
    print('gradient write time to chain',end_wtrgrad - start_wtrgrad)
# Cure Cancer Inc does this
    old_balance = get_balance(agg_addr)
    #print(old_balance)
    gradient_list=Gradient_List(model_id, repo=repo, model=model)
    gradient_list[model_id]
    start_avg_calc=time.time()
avg_gradient=gradient_list.generate_gradient_avg(agg_addr,sa,alpha=2)
end_avg_calc=time.time()
print('avg_compute_write time',end_avg_calc - start_avg_calc)
start_eval=time.time()
end2=time.time()
new_error,updatedModel = model.evaluate_gradient_from_avg(cure_cancer_inc,addr,avg_gradient,scb,prikey,pubkey,validation[0],validation[1],alpha=2)
end_eval=time.time()
print('gradient eval time',end_eval - start_eval)
print("new error from averaged gradients = "+str(new_error))
print(model.best_error)
incentive = (get_balance(agg_addr) - old_balance)
print("incentive = "+str(incentive))
umodelid=repo.submit_updated_model(updatedModel)
model=repo.getUpdatedModel(umodelid)
#end2 = time.time()
print ("total exec time", end2 - start2)
#print('execution time', end - start)