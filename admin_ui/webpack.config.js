const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

const CssRule = {
  test: /\.(scss)$/,
  use: ['style-loader', 'css-loader', 'sass-loader'],
  include: path.resolve(__dirname, './views')
};

module.exports = {
  entry: './static_src/js/index.js',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, './static/dist/'),
  },
  module: {
    // Add loader
    rules: [
      {
        test: /\.(scss)$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader', 'sass-loader']
      },
      {
        test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
        use: [{
        loader: 'file-loader',
          options: {
            name: '[name].[ext]',
            outputPath: 'fonts/'
          }
        }]
      }
    ]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: "[name].css",
      chunkFilename: "[id].css"
    })
  ]
};
