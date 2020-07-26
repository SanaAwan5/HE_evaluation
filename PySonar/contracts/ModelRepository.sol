pragma solidity ^0.5.0;

contract ModelRepository {

  Model[] models;
  Gradient[] grads;
  average[] averages;
  Model [] updatedModels; 

  struct IPFS {
    bytes32 first;
    bytes32 second;
  }

  struct Gradient {

    bool evaluated;

    // submitted from miner
    address payable from;
    IPFS grads;
    uint model_id;

    // submitted from trainer
    uint new_model_error;
    IPFS new_weights;
  }

  struct Model {

    address payable owner;

    IPFS init_weights;
    IPFS weights;

    uint bounty;

    uint initial_error;
    uint best_error;
    uint target_error;

  }

  struct average {

  IPFS avg;

  uint model_id;

  uint numGrads;

  address payable from;

  }

  function transferAmount (address payable reciever, uint amount) private{
    assert(reciever.send(amount));
  }

 function calculateIncentive(uint bounty, uint totalError, uint solvedError) pure public returns(uint total) {
    return (bounty*solvedError) / totalError;
  }

  function addModel (bytes32[] memory _weights, uint initial_error, uint target_error, uint best_error) public payable{

    IPFS memory weights;
    weights.first = _weights[0];
    weights.second = _weights[1];

    Model memory newModel;
    newModel.weights = weights;
    newModel.init_weights = weights;

    newModel.bounty = msg.value;
    newModel.owner = msg.sender;

    newModel.initial_error = initial_error;
    newModel.best_error = best_error;
    newModel.target_error = target_error;

    models.push(newModel);
  }

    function addUpdatedModel (bytes32[] memory _weights, uint initial_error, uint target_error, uint best_error) public payable{

    IPFS memory weights;
    weights.first = _weights[0];
    weights.second = _weights[1];

    Model memory newUpdatedModel;
    newUpdatedModel.weights = weights;
    newUpdatedModel.init_weights = weights;

    newUpdatedModel.bounty = msg.value;
    newUpdatedModel.owner = msg.sender;

    newUpdatedModel.initial_error = initial_error;
    newUpdatedModel.best_error = best_error;
    newUpdatedModel.target_error = target_error;

    updatedModels.push(newUpdatedModel);
  }

  function addAvg(bytes32[] memory _avg,uint model_id, uint numGrads) public {

  IPFS memory avg;
  avg.first = _avg[0];
  avg.second = _avg[1];

  average memory newAvg;
  newAvg.model_id = model_id;
  newAvg.avg = avg;
  newAvg.numGrads = numGrads;
  newAvg.from = msg.sender;

  averages.push(newAvg);
  }

  function evalGradient(uint _gradient_id, uint _new_model_error, bytes32[] memory _new_weights_addr)public {
    // TODO: replace with modifier so that people can't waste gas
    Model storage model = models[grads[_gradient_id].model_id];
   // if(grads[_gradient_id].evaluated == false && msg.sender == model.owner) {

      grads[_gradient_id].new_weights.first = _new_weights_addr[0];
      grads[_gradient_id].new_weights.second = _new_weights_addr[1];
      grads[_gradient_id].new_model_error = _new_model_error;

      
    //Model storage model = models[grads[_gradient_id].model_id];
    if (_new_model_error <= model.best_error && model.target_error <= model.best_error) {
      uint totalError = model.initial_error - model.target_error;
      uint solvedError = model.best_error - _new_model_error;

      uint incentive = calculateIncentive(model.bounty, totalError, solvedError);

      model.best_error = _new_model_error;
      model.weights = grads[_gradient_id].new_weights;
      transferAmount(grads[_gradient_id].from, incentive);
    }

    grads[_gradient_id].evaluated = true;
  }

 function evalGradientfromAvg(uint model_id, uint _new_model_error, bytes32[] memory _new_weights_addr)public {
     // TODO: replace with modifier so that people can't waste gas
    Model storage model = models[model_id];
    //if(grads[_gradient_id].evaluated == false && msg.sender == model.owner) {

      //grads[_gradient_id].new_weights.first = _new_weights_addr[0];
      //grads[_gradient_id].new_weights.second = _new_weights_addr[1];
      //grads[_gradient_id].new_model_error = _new_model_error;
       IPFS memory wt;
       wt.first = _new_weights_addr[0];
       wt.second = _new_weights_addr[1];

       //model.best_error = model.initial_error;
         //Model storage model = models[grads[gradientId].modelId];
    if (_new_model_error <= model.best_error && model.target_error <= model.best_error) {
      uint totalError = model.initial_error - model.target_error;
      uint solvedError = model.best_error - _new_model_error;

      uint incentive = calculateIncentive(model.bounty, totalError, solvedError);

      model.best_error = _new_model_error;
      model.weights = wt;
      transferAmount(averages[model_id].from, incentive);
    }

   // grads[gradientId].evaluated = true;
  }
  
  function addGradient(uint model_id, bytes32[] memory _grad_addr)public {
    //require(models[model_id].owner != 0);
    IPFS memory grad_addr;
    grad_addr.first = _grad_addr[0];
    grad_addr.second = _grad_addr[1];

    IPFS memory new_weights;
    new_weights.first = 0;
    new_weights.second = 0;

    Gradient memory newGrad;
    newGrad.grads = grad_addr;
    newGrad.from = msg.sender;
    newGrad.model_id = model_id;
    newGrad.new_model_error = 0;
    newGrad.new_weights = new_weights;
    newGrad.evaluated=false;

    grads.push(newGrad);
  }

  function getNumModels() view public returns(uint256 model_cnt) {
    return models.length;
  }

  function getNumUpdatedModels() view public returns(uint256 model_cnt) {
    return updatedModels.length;
  }

  function getNumGradientsforModel(uint model_id) view public returns (uint num) {
    num = 0;
    for (uint i=0; i<grads.length; i++) {
      if(grads[i].model_id == model_id) {
        num += 1;
      }
    }
    return num;
  }
  
  function getAvg(uint model_id, uint gradient_id) view public returns (bytes32[] memory) {
    uint num = 0;
    for (uint i=0; i<averages.length; i++) {
      if(averages[i].model_id == model_id) {
        if(averages[i].numGrads == gradient_id) {

          bytes32[] memory _avg = new bytes32[](2);

          _avg[0] = averages[i].avg.first;
          _avg[1] = averages[i].avg.second;


          return (_avg);
        }
        num += 1;
      }
    }
  }
  
  function getGradient(uint model_id, uint gradient_id) view public returns (uint, address,bytes32[] memory,uint,bytes32[] memory) {
    uint num = 0;
    for (uint i=0; i<grads.length; i++) {
      if(grads[i].model_id == model_id) {
        if(num == gradient_id) {

          bytes32[] memory _grad_addr = new bytes32[](2);

          _grad_addr[0] = grads[i].grads.first;
          _grad_addr[1] = grads[i].grads.second;

          bytes32[] memory _new_weghts_addr = new bytes32[](2);
          _new_weghts_addr[0] = grads[i].new_weights.first;
          _new_weghts_addr[1] = grads[i].new_weights.second;

          return (i, grads[i].from, _grad_addr, grads[i].new_model_error, _new_weghts_addr);
        }
        num += 1;
      }
    }
  }

  function getModel(uint model_i) view public returns (address,uint,uint, uint,uint, bytes32[] memory) {

    Model memory currentModel;
    currentModel = models[model_i];
    bytes32[] memory _weights = new bytes32[](2);

    _weights[0] = currentModel.weights.first;
    _weights[1] = currentModel.weights.second;

    return (currentModel.owner, currentModel.bounty, currentModel.initial_error, currentModel.target_error, currentModel.best_error, _weights);
  }

  function getUpdatedModel(uint model_i) view public returns (address,uint,uint, uint,uint, bytes32[] memory) {

    Model memory currentModel;
    currentModel = updatedModels[model_i];
    bytes32[] memory _weights = new bytes32[](2);

    _weights[0] = currentModel.weights.first;
    _weights[1] = currentModel.weights.second;

    return (currentModel.owner, currentModel.bounty, currentModel.initial_error, currentModel.target_error, currentModel.best_error, _weights);
  }

}