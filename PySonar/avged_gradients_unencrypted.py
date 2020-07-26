import warnings
import numpy as np
import phe as paillier
import time
from sonar.contracts_listclass_unencrypted import ModelRepository,Model,Gradient_List
from syft.he.paillier.keys import KeyPair,SecretKey,PublicKey
from syft.nn.linear import LinearClassifier
from sklearn.datasets import load_breast_cancer

start = time.time()
def get_balance(account):
    return repo.web3.fromWei(repo.web3.eth.getBalance(account),'ether')

warnings.filterwarnings('ignore')

# for the purpose of the simulation, we're going to split our dataset up amongst
# the relevant simulated users

diabetes = load_breast_cancer()
y = diabetes.target
X = diabetes.data

validation = (X[46:51],y[46:51])
anonymous_diabetes_users = (X[52:],y[52:])

# we're also going to initialize the model trainer smart contract, which in the
# real world would already be on the blockchain (managing other contracts) before
# the simulation begins

# ATTENTION: copy paste the correct address (NOT THE DEFAULT SEEN HERE) from truffle migrate output.
repo = ModelRepository('0xEf38C644F9FbF25ADB329653BB16B0D3Cb766bC7') # blockchain hosted model repository

# we're going to set aside 10 accounts for our 42 patients
# Let's go ahead and pair each data point with each patient's 
# address so that we know we don't get them confused
patient_addresses = repo.web3.eth.accounts[1:10]
anonymous_diabetics = list(zip(patient_addresses,
                               anonymous_diabetes_users[0],
                               anonymous_diabetes_users[1]))

# we're going to set aside 1 account for Cure Diabetes Inc
cure_diabetes_inc = repo.web3.eth.accounts[1]
agg_addr = repo.web3.eth.accounts[2]

pubkey,prikey = KeyPair().generate(n_length=1024)
#pubkey,prikey=paillier.paillier.generate_paillier_keypair()
diabetes_classifier = LinearClassifier(desc="DiabetesClassifier",n_inputs=30,n_labels=2)
initial_error = diabetes_classifier.evaluate(validation[0],validation[1])
#diabetes_classifier.encrypt(pubkey)
s1,s2=paillier.paillier.genKeyShares(prikey.sk,pubkey.pk)
st=SecretKey(s1)
sab=SecretKey(s2)
s3,s4=paillier.paillier.genKeyShares(s2,pubkey.pk)
sa=SecretKey(s3)
scb=SecretKey(s4)

diabetes_model = Model(owner=cure_diabetes_inc,
                       syft_obj = diabetes_classifier,
                       bounty = 2,
                       initial_error = initial_error,
                       target_error = 100,
                       best_error= initial_error
                      )
model_id = repo.submit_model(diabetes_model)
print('initial error',initial_error)
model=repo[model_id]
diabetic_address,input_data,target_data = anonymous_diabetics[0]
gradient=model.generate_gradient(diabetic_address,input_data,target_data)
#model.submit_transformed_gradients(gradient,st)
model.submit_gradient(gradient)

old_balance = get_balance(diabetic_address)
print(old_balance)
gradient_list=Gradient_List(model_id, repo=repo, model=model)
gradient_list[model_id]
model=repo[model_id]
avg_gradient=gradient_list.generate_gradient_avg(agg_addr,alpha=2)
new_error,updatedModel = model.evaluate_gradient_from_avg(cure_diabetes_inc,agg_addr,avg_gradient,validation[0],validation[1])
print('new_error',new_error)
new_balance = get_balance(diabetic_address)
incentive = new_balance - old_balance
print(incentive)
print(repo[model_id])
for i,(addr, input, target) in enumerate(anonymous_diabetics):
    model = repo[model_id]
    print('model_id',model_id)
# patient is doing this
    gradient=model.generate_gradient(addr,input,target)
    model.submit_gradient(gradient)
# Cure Diabetes Inc does this
    old_balance = get_balance(agg_addr)
    print(old_balance)
    gradient_list=Gradient_List(model_id, repo=repo, model=model)
    gradient_list[model_id]
    avg_gradient=gradient_list.generate_gradient_avg(agg_addr,alpha=2)
    new_error,updatedModel = model.evaluate_gradient_from_avg(cure_diabetes_inc,agg_addr,avg_gradient,validation[0],validation[1],alpha=2)
    print("new error from averaged gradients = "+str(new_error))
    print(model.best_error)
    incentive = (get_balance(agg_addr) - old_balance)
    print("incentive = "+str(incentive))
umodelid=repo.submit_updated_model(updatedModel)
model=repo.getUpdatedModel(umodelid)
end = time.time()
print('execution time', end - start)