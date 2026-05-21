const HtmlWebpackPlugin = require('html-webpack-plugin');
const path = require('path');

module.exports = {
  entry: './src/index.jsx',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
  },
  module: {
    rules: [{
      test: /\.(js|jsx)$/,
      use: 'babel-loader',
      exclude: /node_modules/,
      
    },
    {
      test: /\.css$/,
      use: ['style-loader', 'css-loader'],
    }],
  },
  resolve: {
    // This allows both JS and JSX file extensions to be tried when resolving imports
    extensions: ['.js', '.jsx'],
  },
  plugins: [
    new HtmlWebpackPlugin({ template: './index.html' }),
  ],
  devServer: {
    port: 3000,
    proxy: [{ context: ['/api'], target: 'http://localhost:8000' }],
    // Edit this link if you deploy the backend
  },
};
