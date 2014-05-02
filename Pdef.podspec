Pod::Spec.new do |s|
  s.name         = "Pdef"
  s.version      = "2.0.0"
  s.summary      = "Pdef format and client."
  s.homepage     = "https://github.com/pdef/pdef-objc"
  s.license      = 'Apache License 2.0'

  s.author       = { "Ivan Korobkov" => "ivan.korobkov@gmail.com" }
  s.source       = { :git => "https://github.com/pdef/pdef.git", :tag => "v2.0.0" }
  s.requires_arc = true

  s.ios.deployment_target = '6.0'
  s.osx.deployment_target = '10.8'

  s.source_files  = 'Pdef', 'Pdef/*.{h,m}'
  s.public_header_files = 'Pdef/*.h'

  s.dependency 'AFNetworking', '~> 2.0'
  s.dependency 'ReactiveCocoa', '~> 2.3'
end
