import React, { useState } from 'react';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [data, setData] = useState('');
  const [result, setResult] = useState(null);
  const [ast, setAst] = useState(null);

  const handleCreateAST = async () => {
    try {
      const cleanedQuery = query
        .replace(/^\[|\]$/g, '')
        .split(/\)\s*,\s*\(/);

      let response;

      if (cleanedQuery.length > 1) {
        response = await axios.post('http://localhost:5001/combine_rules', { rules: cleanedQuery });
      } else {
        response = await axios.post('http://localhost:5001/parse_rule', { rule: cleanedQuery[0] });
      }

      const astResponse = await axios.get(`http://localhost:5001/get_ast?ruleId=${response.data.ruleId}`);
      setAst(astResponse.data);

      toast.success(`AST created successfully with ID: ${response.data.ruleId}`);
    } catch (error) {
      console.error(error);
      toast.error('An error occurred while creating the AST. Please check your input and try again.');
    }
  };

  const handleEvaluate = async () => {
    try {
      const parsedData = JSON.parse(data);
      const response = await axios.post('http://localhost:5001/evaluate', { ruleId: 1, data: parsedData });
      setResult(response.data.result);
      const resultText = response.data.result ? 'True' : 'False';
      toast.success(`Evaluation successful: ${resultText}`);
    } catch (error) {
      if (error instanceof SyntaxError) {
        toast.error('Invalid JSON format in the data input. Please correct it and try again.');
      } else {
        console.error(error);
        toast.error('An error occurred while evaluating the data. Please check your input and try again.');
      }
    }
  };

  return (
    <div className="App">
      <ToastContainer />
      <div className="left-pane">
        <h1>Rule Parser and Evaluator</h1>

        <div className="input-container">
          <label>Query Input:</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a rule or an array of rules, one per line"
          />
          <button onClick={handleCreateAST}>Create AST</button>
        </div>

        <div className="input-container">
          <label>Data Input:</label>
          <textarea
            value={data}
            onChange={(e) => setData(e.target.value)}
            placeholder="Enter data as JSON"
          />
          <button onClick={handleEvaluate}>Evaluate</button>
        </div>

        {result !== null && (
          <div className={`result ${result ? 'true' : 'false'}`}>
            <h2>Result: {result ? 'True' : 'False'}</h2>
          </div>
        )}
      </div>

      <div className="right-pane">
        <h2>Formed AST</h2>
        <div className="ast-container">
          {ast ? <TreeNode node={ast} /> : 'No AST available'}
        </div>
      </div>
    </div>
  );
}

const TreeNode = ({ node }) => {
  return (
    <div className="tree-node">
      <div className="node-content">
        {node.type === 'operator' ? node.value : node.value}
      </div>
      {node.left || node.right ? (
        <div className="children">
          {node.left && (
            <div className="child">
              <TreeNode node={node.left} />
            </div>
          )}
          {node.right && (
            <div className="child">
              <TreeNode node={node.right} />
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default App;
