import json
import copy
from web3 import Web3, HTTPProvider, KeepAliveRPCProvider
import numpy as np
from .paillier import EncryptedNumber

from sonar.ipfs import IPFS



class Gradient():
    def __init__(self, owner, grad_values, gradient_id, new_model_error=None,
                 new_weights=None):
        self.owner = owner
        self.grad_values = grad_values
        self.id = gradient_id

        self.new_model_error = new_model_error
        self.new_weights = new_weights

class Gradient_List():
    def __init__(self, model_id,repo=None, model=None):
        self.model_id = model_id
        self.gradient_list = []
        self.repo=repo
        self.model = model

    def __getitem__(self, modelid):
        num_gradients = self.repo.call.getNumGradientsforModel(self.model_id)
        gradient_id = 0
        if num_gradients > 0:
            for i in range (0,num_gradients):
                g=self.model[gradient_id]
                self.gradient_list.append(g)
                gradient_id = gradient_id + 1
        else:
            print ("gradient list is empty") 
        return self.gradient_list

    def __len__(self):
        return self.repo.call.getNumGradientsforModel(self.model_id)

    def generate_gradient_avg(self,agg_addr, alpha = 1):
        length = self.repo.call.getNumGradientsforModel(self.model_id)
        print('len',length)
        num_gradients = self.repo.call.getNumGradientsforModel(self.model_id)
        gradient_id = 0
        if num_gradients > 0:
            for i in range (0,num_gradients):
                g=self.model[gradient_id]
                self.gradient_list.append(g)
                gradient_id = gradient_id + 1
        else:
            print ("gradient list is empty") 
        self.gradient_list[0].grad_values.data = self.gradient_list[0].grad_values.data;
        print('type',type(self.gradient_list[0].grad_values.data[0][0]))
        for i in range(1,length):
            self.gradient_list[0].grad_values.data += self.gradient_list[i].grad_values.data 
        self.gradient_list[0].grad_values.data = self.gradient_list[0].grad_values.data /length
        #print('shaped',np.shape(self.gradient_list[0].grad_values.data))
        #print('self.gradient_list[0].grad_values.data',type(self.gradient_list[0].grad_values.data[0][0]))
        #print('self.gradient_list[0].grad_values.data.sum()',type(self.gradient_list[0].grad_values.data.sum()))
        avg = self.gradient_list[0].grad_values.data
        out=list()
        sh=avg.shape
        avged_result = []
        #print('avgedresult',type(avg))
        if(type(avg) == np.ndarray):
            avg_ = avg.reshape(-1)
            for v in avg_:
                #print('vvvvbefore',type(v))
                
                #print('typeofout',type(transform_key.transform(v)))
                #temp=transform_key.sk.transform(v)
                out.append(v)

                #print('outis',transform_key.transform(v))          
                #print('vvvvvvtransform',type(temp))
                
        avged_result = np.array(out).reshape(sh)
       
        numgrads=length
        #print('numgrads',numgrads)
        self.repo.submit_avg(agg_addr,avged_result, self.model,length)
        #print('typeofout',type(out[0]))
        #print('typeofout',type(np.array(out).reshape(sh)))
        return np.array(out).reshape(sh)



class Model():
    def __init__(self, owner, syft_obj, bounty, initial_error, target_error,best_error,
                 model_id=None, repo=None, gradient_list=None):
        self.owner = owner
        self.syft_obj = syft_obj
        self.bounty = bounty
        self.initial_error = initial_error
        self.best_error = best_error  # TODO: get this
        self.target_error = target_error
        self.model_id = model_id
        self.repo = repo
        self.gradient_list = Gradient_List(self.model_id)

    def __getitem__(self, gradient_id):
        (gradient_id, grad_owner, mca, new_model_error,
         nwa) = self.repo.call.getGradient(self.model_id, gradient_id)
        grad_values = \
            self.repo.ipfs.retrieve(IPFSAddress().from_ethereum(mca))
        if(new_model_error != 0):
            new_weights = \
                self.repo.ipfs.retrieve(IPFSAddress().from_ethereum(nwa))
        else:
            new_weights = None
            new_model_error = None
        g = Gradient(grad_owner, grad_values, gradient_id,
                     new_model_error, new_weights)
        return g

    def __len__(self):
        return self.repo.call.getNumGradientsforModel(self.model_id)

    def submit_gradient(self,gradient):
        #gradient = self.generate_encrypted_gradient(owner, input, target, pubkey)
        self.repo.submit_gradient(gradient.owner,
                                  self.model_id, gradient.grad_values)

        

    def generate_gradient(self, owner, input, target):
        grad_values = self.syft_obj.generate_gradient(input, target)
        gradient = Gradient(owner, grad_values, None)
        return gradient

    def generate_encrypted_gradient(self, owner, input, target,pubkey):
        grad_values = self.syft_obj.generate_encrypted_gradient(input, target,pubkey)
        #print('type grad_values',type(grad_values))
        #grad_values = grad_values.transform(st)
        gradient = Gradient(owner, grad_values, None)
        print('typeof gradient.grad_values.data[0][0]',type(gradient.grad_values.data[0][0]))
        return gradient
    """def submit_transformed_gradients(self,st):
        num_gradients = self.repo.call.getNumGradientsforModel(self.model_id)
        gradient_id = 0
        g=self[gradient_id]
        if num_gradients > 0:
            for i in range (0,num_gradients):
                g=self[gradient_id]
                g.grad_values = g.grad_values.transform(st)
                self.repo.submit_transformed_gradient(g.owner, self.model_id, g.grad_values)
                gradient_id = gradient_id + 1
                print('typeof gradient.grad_values.data[0][0]',type(g.grad_values.data[0][0]))
        else:
            print ("No gradients found for model")"""

    def submit_transformed_gradients(self,gradient,st):
        gradient.grad_values = gradient.grad_values.transform(st)
        self.repo.submit_gradient(gradient.owner,
                                  self.model_id, gradient.grad_values)
        
    

    def evaluate_gradient(self, addr, gradient, prikey, pubkey, inputs,
                          targets, alpha=1):

        candidate = copy.deepcopy(self.syft_obj)
        gradient.grad_values = gradient.grad_values.decrypt(prikey)
        candidate.weights -= gradient.grad_values * alpha
        #candidate.weights = candidate.weights.decrypt(prikey)
        #candidate.encrypted = False
        new_model_error = candidate.evaluate(inputs, targets)
        tx = self.repo.get_transaction(from_addr=addr)
        ipfs_address = self.repo.ipfs.store(candidate.encrypt(pubkey))
        tx.evalGradient(gradient.id, new_model_error,
                        IPFSAddress().to_ethereum(ipfs_address))
        #print('hello')
        return new_model_error

    def evaluate_gradient_from_avg(self,addr,agg_addr,avg, inputs, targets, alpha=1):
        length = self.repo.call.getNumGradientsforModel(self.model_id)
        nwa = self.repo.call.getAvg(self.model_id,length)
        new_avg = self.repo.ipfs.retrieve(IPFSAddress().from_ethereum(nwa))
        #print('avggrad is', type(avg))
        out=list()
        sh=new_avg.shape
        if(type(new_avg) == np.ndarray):
            new_avg_ = new_avg.reshape(-1)
            for v in new_avg_:
                #print('vvvvvvbefore',type(v))
                #print('v is',v)
                out.append(v)
                #print('vvvvvv',type(transform_key.sk.finalDecrypt(v)))
        avg_grad_values = np.array(out).reshape(sh)
        
        candidate = copy.deepcopy(self.syft_obj)
        #candidate.weights=candidate.weights.decrypt(prikey)
        candidate.weights -= (avg_grad_values * alpha) 
        #candidate.weights = candidate.weights.decrypt(prikey)
        candidate.encrypted = False

        new_model_error = candidate.evaluate(inputs, targets)

        tx = self.repo.get_transaction(from_addr=addr)
        ipfs_address = self.repo.ipfs.store(candidate)
        #length_ = length - 1
        tx.evalGradientfromAvg(self.model_id,agg_addr, new_model_error,
                        IPFSAddress().to_ethereum(ipfs_address))
        updatedModel=Model(self.owner,candidate,self.bounty,self.initial_error,self.target_error,self.model_id,self)

        #self.repo.submit_updated_model(updatedModel)

        return new_model_error,updatedModel

    def __str__(self):
        s = ""
        s += "Desc:" + str(self.syft_obj.desc) + "\n"
        s += "Owner:" + str(self.owner) + "\n"
        s += "Bounty:" + str(self.bounty) + "\n"
        s += "Initial Error:" + str(self.initial_error) + "\n"
        s += "Best Error:" + str(self.best_error) + "\n"
        s += "Target Error:" + str(self.target_error) + "\n"
        s += "Model ID:" + str(self.model_id) + "\n"
        s += "Num Grads:" + str(len(self)) + "\n"
        return s

    def __repr__(self):
        return self.__str__()


class ModelRepository():
    """This class is a python client wrapper around the Sonar contract,
    giving easy to use python functions around the contract's functionality. It
    currently assumes we are running on a local testrpc Ethereum blockchain."""

    def __init__(self, contract_address, account=None,
                 ipfs=IPFS('127.0.0.1', 5001),
                 web3_host='localhost', web3_port=8545):
        """Creates the base blockchain client object (web3) then
         connects to the Sonar contract.
        It assumes you're working with a local testrpc blockchain."""

        self.ipfs = ipfs
        #self.web3 = Web3(KeepAliveRPCProvider(host=web3_host,port=str(web3_port)))
        self.web3 = Web3(HTTPProvider('http://18.224.21.109:8545'))
        #self.web3 = Web3(Web3.EthereumTesterProvider()) 
        #self.web3 = Web3(Web3.EthereumTesterProvider())
        print('web3.version.api',self.web3.version.api)

        if account is not None:
            self.account = account
        else:
            print("No account submitted... using default[2]")
            self.account = self.web3.eth.accounts[2]

        self.connect_to_contract(contract_address)

    def connect_to_contract(self, contract_address):
        """Connects to the Sonar contract using its address and ABI"""

        f = open('ModelRepository.abi', 'r')
        abi = json.loads(f.read())
        f.close()

        self.contract = self.web3.eth.contract(abi=abi)

        self.contract_address = contract_address

        self.call = self.contract.call({
            "from": self.account,
            "to": self.contract_address,
        })
        print("Connected to ModelRepository:" +
              str(self.contract_address))

    def get_transaction(self, from_addr, value=None):
        """I consistently forget the conventions for executing transactions against
        compiled contracts. This function helps that to be easier for me."""

        txn = {}
        txn["from"] = from_addr
        txn["to"] = self.contract_address

        if value is not None:
            txn["value"] = int(value)

        transact_raw = self.contract.transact(txn)
        return transact_raw

    def submit_model(self, model):
        """This accepts a model from syft.nn, loads it into IPFS, and uploads
        the IPFS address to the blockchain.
        TODO: better way to storing IPFS addresses on the blockchain.
        See https://github.com/OpenMined/Sonar/issues/19"""
        ipfs_address = self.ipfs.store(model.syft_obj)
        deploy_tx = self.get_transaction(
            model.owner,
            value=self.web3.toWei(model.bounty, 'ether'))
        deploy_tx.addModel(IPFSAddress().to_ethereum(ipfs_address),
                           model.initial_error, model.target_error,model.best_error)
        return self.call.getNumModels() - 1

    def submit_updated_model(self, model):
        """This accepts a model from syft.nn, loads it into IPFS, and uploads
        the IPFS address to the blockchain.
        TODO: better way to storing IPFS addresses on the blockchain.
        See https://github.com/OpenMined/Sonar/issues/19"""
        ipfs_address = self.ipfs.store(model.syft_obj)
        deploy_tx = self.get_transaction(
            model.owner,
            value=self.web3.toWei(model.bounty, 'ether'))
        deploy_tx.addUpdatedModel(IPFSAddress().to_ethereum(ipfs_address),
                           model.initial_error, model.target_error,model.best_error)
        return self.call.getNumUpdatedModels() - 1

    def submit_avg(self,agg_addr,avg,model,length):
        ipfs_address = self.ipfs.store(avg)
        deploy_tx = self.get_transaction(agg_addr).addAvg(IPFSAddress().to_ethereum(ipfs_address),model.model_id,length)

    def submit_gradient(self, from_addr, model_id, grad):
        ipfs_address = self.ipfs.store(grad)
        self.get_transaction(from_addr).addGradient(
            model_id, IPFSAddress().to_ethereum(ipfs_address))
        return self.call.getNumGradientsforModel(model_id) - 1

    def get_avg(model_id,length):
        if(model_id < len(self)):
            return self.call.getAvg(model_id,length)

    def __getitem__(self, model_id):
        if(model_id < len(self)):

            (owner, bounty, initial_error, target_error,best_error, mca) = \
                self.call.getModel(model_id)
            syft_obj = \
                self.ipfs.retrieve(IPFSAddress().from_ethereum(mca))
            model = Model(owner, syft_obj, self.web3.fromWei(bounty, 'ether'),
                          initial_error, target_error,best_error, model_id, self)

            return model

    def getUpdatedModel(self, model_id):
        length=self.call.getNumUpdatedModels()
        if(model_id < length):

            (owner, bounty, initial_error, target_error,best_error, mca) = \
                self.call.getUpdatedModel(model_id)
            syft_obj = \
                self.ipfs.retrieve(IPFSAddress().from_ethereum(mca))
            updatedModel = Model(owner, syft_obj, self.web3.fromWei(bounty, 'ether'),
                          initial_error, target_error, best_error, model_id, self)

            return updatedModel

    def __len__(self):
        return self.call.getNumModels()

    def getNumUpdatedModels(self):
        return self.call.getNumUpdatedModels()


class IPFSAddress:
    def from_ethereum(self, two_bytes32_rep):
        return two_bytes32_rep[0] + two_bytes32_rep[1][0:14]
#         return bytearray.fromhex("".join(two_bytes32_representation)
#                        .replace("0x", "")).decode().replace("0", "")

    def to_ethereum(self, ipfs_hash):
        return [ipfs_hash[0:32], ipfs_hash[32:]]